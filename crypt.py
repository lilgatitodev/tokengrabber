#!/usr/bin/env python3
import argparse, ast, base64, dataclasses, enum, functools, hashlib, io, keyword, logging, marshal, os, random, secrets, string, sys, typing, zlib
from cryptography.fernet import Fernet, InvalidToken
from pathlib import Path
from types import ModuleType, SimpleNamespace

_RESERVED = set(keyword.kwlist) | {
    "True","False","None","self","cls","Fernet","InvalidToken",
    "argparse","base64","dataclasses","enum","functools","hashlib","io",
    "logging","marshal","os","secrets","sys","typing","zlib","compile","exec",
    "main","__name__","__file__","__builtins__","__package__",
    "_a","_av","_b","_c","_d","_e","_g","_h","_i","_k","_m","_n","_o","_p",
    "_pt","_r","_s","_si","_so","_t","_ti","_to","_u","_v","_w","_x","_y",
}
_LOGGER_NAMES = ["rb","core","loader","rsrc","bundle","vault","asset","pkg","module","rt","kernel","host"]
_LOG_FORMATS = [
    "%(name)s [%(levelname)s] %(message)s",
    "[%(levelname)s] %(name)s: %(message)s",
    "%(name)s | %(levelname)s | %(message)s",
    "%(levelname)s %(name)s %(message)s",
    "%(asctime)s %(name)s %(levelname)s %(message)s",
]
_ITER_CHOICES = [400_000,440_000,480_000,520_000,560_000,600_000]
_NAMES = [
    "logger_var","log_format_var",
    "exc_base","exc_manifest","exc_codec","exc_decrypt","exc_pass",
    "enum_fmt","enum_codec","enum_kdf","enum_stage",
    "em_fmt_zlib","em_fmt_plain","em_codec_url","em_codec_std","em_kdf_pbkdf2",
    "em_stage_decode","em_stage_outer","em_stage_inner","em_stage_decomp",
    "cls_manifest","cls_context","cls_cipher_proto","cls_cipher_backend","cls_bundle",
    "mf_version","mf_format","mf_codec","mf_kdf","mf_iter","mf_salt_size","mf_source","mf_bytecode","mf_method_lines",
    "cx_manifest","cx_raw","cx_decoded","cx_key1","cx_key2","cx_middle","cx_plain","cx_pass",
    "reg_codec","reg_kdf","reg_backend","reg_stage",
    "fn_reg_codec","fn_reg_kdf","fn_reg_stage",
    "fn_codec_url","fn_codec_std","fn_kdf_pbkdf2",
    "fn_lookup_codec","fn_lookup_kdf","fn_lookup_backend",
    "cipher_method","cipher_name_attr",
    "prefix_inner_var","prefix_outer_var",
    "bundle_manifest_attr","bundle_data_attr","bundle_method",
    "fn_resolve_pass",
    "fn_stage_decode","fn_stage_outer","fn_stage_inner","fn_stage_decomp",
    "var_default_pipeline",
    "fn_run","fn_namespace","fn_materialize","fn_execute",
    "fn_parse_args","fn_config_log","fn_strict",
    "var_binding","fn_compute_binding",
]
_SALT_SIZE = 16


def _make_name(rng, taken):
    while True:
        n = rng.choice([3,4,5])
        name = "_" + rng.choice(string.ascii_letters) + "".join(rng.choice(string.ascii_letters+string.digits) for _ in range(n-1))
        if name in _RESERVED or name in taken:
            continue
        taken.add(name)
        return name


def _unique_bytes(rng, count, lo=0x10, hi=0xFF):
    pool = list(range(lo, hi+1))
    rng.shuffle(pool)
    return pool[:count]


def new_polymorph():
    rng = random.Random(secrets.token_bytes(16))
    p = SimpleNamespace()
    taken = set()
    for n in _NAMES:
        setattr(p, n, _make_name(rng, taken))
    p.logger_name = rng.choice(_LOGGER_NAMES)
    p.log_format = rng.choice(_LOG_FORMATS)
    a, b = _unique_bytes(rng, 2); p.val_fmt_zlib, p.val_fmt_plain = a, b
    a, b = _unique_bytes(rng, 2); p.val_codec_url, p.val_codec_std = a, b
    p.val_kdf_pbkdf2 = _unique_bytes(rng, 1)[0]
    s = _unique_bytes(rng, 4); p.val_stage_decode, p.val_stage_outer, p.val_stage_inner, p.val_stage_decomp = s
    px = _unique_bytes(rng, 2, lo=0x01, hi=0xFE); p.prefix_inner_val, p.prefix_outer_val = px
    p.pbkdf2_iterations = rng.choice(_ITER_CHOICES)
    p.salt_size = _SALT_SIZE
    return p


def _derive_key(passphrase, salt, iterations):
    raw = hashlib.pbkdf2_hmac("sha256", passphrase, salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(raw)


def encrypt(plaintext, passphrase, iterations, inner_prefix, outer_prefix, binding):
    salt_inner = secrets.token_bytes(_SALT_SIZE)
    salt_outer = secrets.token_bytes(_SALT_SIZE)
    key_inner = _derive_key(passphrase, binding + inner_prefix + salt_inner, iterations)
    key_outer = _derive_key(passphrase, binding + outer_prefix + salt_outer, iterations)
    inner_token = Fernet(key_inner).encrypt(plaintext)
    outer_token = Fernet(key_outer).encrypt(salt_inner + inner_token)
    return salt_outer + outer_token


def strip_docstrings(source):
    tree = ast.parse(source)
    class _S(ast.NodeTransformer):
        def _strip(self, node):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                if len(node.body) == 1:
                    node.body[0] = ast.Pass()
                else:
                    node.body = node.body[1:]
            return node
        def visit_Module(self, n): n = self._strip(n); self.generic_visit(n); return n
        def visit_FunctionDef(self, n): n = self._strip(n); self.generic_visit(n); return n
        def visit_AsyncFunctionDef(self, n): n = self._strip(n); self.generic_visit(n); return n
        def visit_ClassDef(self, n): n = self._strip(n); self.generic_visit(n); return n
    _S().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _fmt_payload(payload, width=72, indent="        "):
    encoded = base64.urlsafe_b64encode(payload)
    chunks = [encoded[i:i+width] for i in range(0, len(encoded), width)]
    if not chunks:
        return f'{indent}b""'
    return "\n".join(f"{indent}{c!r}" for c in chunks)


def _emit_exceptions(p):
    return "\n".join([
        f"class {p.exc_base}(RuntimeError): pass",
        f"class {p.exc_manifest}({p.exc_base}): pass",
        f"class {p.exc_codec}({p.exc_base}): pass",
        f"class {p.exc_decrypt}({p.exc_base}): pass",
        f"class {p.exc_pass}({p.exc_base}): pass",
    ])


def _emit_enums(p):
    return "\n".join([
        f"class {p.enum_fmt}(enum.IntEnum): {p.em_fmt_zlib} = {p.val_fmt_zlib:#x}; {p.em_fmt_plain} = {p.val_fmt_plain:#x}",
        f"class {p.enum_codec}(enum.IntEnum): {p.em_codec_url} = {p.val_codec_url:#x}; {p.em_codec_std} = {p.val_codec_std:#x}",
        f"class {p.enum_kdf}(enum.IntEnum): {p.em_kdf_pbkdf2} = {p.val_kdf_pbkdf2:#x}",
        f"class {p.enum_stage}(enum.IntEnum): {p.em_stage_decode} = {p.val_stage_decode:#x}; {p.em_stage_outer} = {p.val_stage_outer:#x}; {p.em_stage_inner} = {p.val_stage_inner:#x}; {p.em_stage_decomp} = {p.val_stage_decomp:#x}",
    ])


def _emit_dataclasses(p):
    manifest_fields = f"{p.mf_version}: int; {p.mf_format}: {p.enum_fmt}; {p.mf_codec}: {p.enum_codec}; {p.mf_kdf}: {p.enum_kdf}; {p.mf_iter}: int; {p.mf_salt_size}: int; {p.mf_source}: str; {p.mf_bytecode}: bool"
    return "\n".join([
        "@dataclasses.dataclass(frozen=True)",
        f"class {p.cls_manifest}:",
        f"    {manifest_fields}",
        f"    def {p.mf_method_lines}(self):",
        "        for _x in dataclasses.fields(self):",
        "            _y = getattr(self, _x.name)",
        "            if isinstance(_y, enum.IntEnum): _y = '0x%x' % int(_y)",
        "            yield '{0}: {1}'.format(_x.name, _y)",
        "@dataclasses.dataclass",
        f"class {p.cls_context}:",
        f"    {p.cx_manifest}: {p.cls_manifest}",
        f"    {p.cx_raw}: bytes",
        f"    {p.cx_decoded}: typing.Optional[bytes] = None",
        f"    {p.cx_key1}: typing.Optional[bytes] = None",
        f"    {p.cx_key2}: typing.Optional[bytes] = None",
        f"    {p.cx_middle}: typing.Optional[bytes] = None",
        f"    {p.cx_plain}: typing.Optional[bytes] = None",
        f"    {p.cx_pass}: typing.Optional[bytes] = None",
    ])


def _emit_codec_registry(p):
    return "\n".join([
        f"{p.reg_codec}: typing.Dict[{p.enum_codec}, typing.Callable[[bytes], bytes]] = {{}}",
        f"def {p.fn_reg_codec}(_c):",
        f"    def _w(fn): {p.reg_codec}[_c] = fn; return fn",
        f"    return _w",
        f"@{p.fn_reg_codec}({p.enum_codec}.{p.em_codec_url})",
        f"def {p.fn_codec_url}(_d: bytes) -> bytes: return base64.urlsafe_b64decode(_d)",
        f"@{p.fn_reg_codec}({p.enum_codec}.{p.em_codec_std})",
        f"def {p.fn_codec_std}(_d: bytes) -> bytes: return base64.standard_b64decode(_d)",
        f"def {p.fn_lookup_codec}(_c: {p.enum_codec}):",
        f"    if _c not in {p.reg_codec}: raise {p.exc_codec}('codec {{0}}'.format(int(_c)))",
        f"    return {p.reg_codec}[_c]",
    ])


def _emit_kdf_registry(p):
    return "\n".join([
        f"{p.reg_kdf}: typing.Dict[{p.enum_kdf}, typing.Callable[[bytes, bytes, int], bytes]] = {{}}",
        f"def {p.fn_reg_kdf}(_a):",
        f"    def _w(fn): {p.reg_kdf}[_a] = fn; return fn",
        f"    return _w",
        f"@{p.fn_reg_kdf}({p.enum_kdf}.{p.em_kdf_pbkdf2})",
        f"def {p.fn_kdf_pbkdf2}(_p: bytes, _s: bytes, _i: int) -> bytes:",
        f"    _r = hashlib.pbkdf2_hmac('sha256', _p, _s, _i, dklen=32)",
        f"    return base64.urlsafe_b64encode(_r)",
        f"def {p.fn_lookup_kdf}(_a: {p.enum_kdf}):",
        f"    if _a not in {p.reg_kdf}: raise {p.exc_manifest}('kdf {{0}}'.format(int(_a)))",
        f"    return {p.reg_kdf}[_a]",
    ])


def _emit_cipher_backend(p):
    return "\n".join([
        f"class {p.cls_cipher_proto}(typing.Protocol):",
        f"    {p.cipher_name_attr}: str",
        f"    def {p.cipher_method}(self, _p: bytes, _k: bytes) -> bytes: ...",
        f"class {p.cls_cipher_backend}:",
        f"    {p.cipher_name_attr} = 'f'",
        f"    def {p.cipher_method}(self, _p: bytes, _k: bytes) -> bytes:",
        f"        try: return Fernet(_k).decrypt(_p)",
        f"        except InvalidToken as _e: raise {p.exc_decrypt}('rejected') from _e",
        f"{p.reg_backend}: typing.Dict[{p.enum_fmt}, typing.Callable[[], {p.cls_cipher_proto}]] = {{{p.enum_fmt}.{p.em_fmt_zlib}: {p.cls_cipher_backend}, {p.enum_fmt}.{p.em_fmt_plain}: {p.cls_cipher_backend}}}",
        f"def {p.fn_lookup_backend}(_f: {p.enum_fmt}):",
        f"    _g = {p.reg_backend}.get(_f)",
        f"    if _g is None: raise {p.exc_manifest}('backend {{0}}'.format(int(_f)))",
        f"    return _g()",
    ])


def _emit_prefix_bytes(p):
    return f"{p.prefix_inner_var} = bytes([{p.prefix_inner_val:#x}]); {p.prefix_outer_var} = bytes([{p.prefix_outer_val:#x}])"


def _emit_bundle_class(p, payload, source_name):
    args = (
        f"{p.mf_version}=1, "
        f"{p.mf_format}={p.enum_fmt}.{p.em_fmt_zlib}, "
        f"{p.mf_codec}={p.enum_codec}.{p.em_codec_url}, "
        f"{p.mf_kdf}={p.enum_kdf}.{p.em_kdf_pbkdf2}, "
        f"{p.mf_iter}={p.pbkdf2_iterations}, "
        f"{p.mf_salt_size}={p.salt_size}, "
        f"{p.mf_source}={source_name!r}, "
        f"{p.mf_bytecode}=False"
    )
    return "\n".join([
        f"class {p.cls_bundle}:",
        f"    {p.bundle_manifest_attr} = {p.cls_manifest}({args})",
        f"    {p.bundle_data_attr}: bytes = (",
        _fmt_payload(payload),
        "    )",
        "    @classmethod",
        f"    def {p.bundle_method}(cls): return {p.cls_context}({p.cx_manifest}=cls.{p.bundle_manifest_attr}, {p.cx_raw}=cls.{p.bundle_data_attr})",
    ])


def _emit_password_resolver(p, password_value):
    return "\n".join([
        f"def {p.fn_resolve_pass}() -> bytes:",
        f"    _c = {password_value.encode('utf-8')!r}",
        f"    return _c",
    ])


def _emit_stage_registry_decorator(p):
    return "\n".join([
        f"{p.reg_stage}: typing.Dict[{p.enum_stage}, typing.Callable[[{p.cls_context}], None]] = {{}}",
        f"def {p.fn_reg_stage}(_s):",
        f"    def _w(fn):",
        f"        @functools.wraps(fn)",
        f"        def _u(_x):",
        f"            {p.logger_var}.debug('%x', int(_s)); fn(_x); {p.logger_var}.debug('/%x', int(_s))",
        f"        {p.reg_stage}[_s] = _u; return _u",
        f"    return _w",
    ])


def _emit_stages(p):
    return "\n".join([
        f"@{p.fn_reg_stage}({p.enum_stage}.{p.em_stage_decode})",
        f"def {p.fn_stage_decode}(_x: {p.cls_context}) -> None:",
        f"    _x.{p.cx_decoded} = {p.fn_lookup_codec}(_x.{p.cx_manifest}.{p.mf_codec})(_x.{p.cx_raw})",
        f"@{p.fn_reg_stage}({p.enum_stage}.{p.em_stage_outer})",
        f"def {p.fn_stage_outer}(_x: {p.cls_context}) -> None:",
        f"    if _x.{p.cx_pass} is None: raise {p.exc_pass}('p')",
        f"    if _x.{p.cx_decoded} is None: raise {p.exc_base}('d')",
        f"    _so = _x.{p.cx_decoded}[:_x.{p.cx_manifest}.{p.mf_salt_size}]",
        f"    _to = _x.{p.cx_decoded}[_x.{p.cx_manifest}.{p.mf_salt_size}:]",
        f"    _g = {p.fn_lookup_kdf}(_x.{p.cx_manifest}.{p.mf_kdf})",
        f"    _x.{p.cx_key1} = _g(_x.{p.cx_pass}, {p.var_binding} + {p.prefix_outer_var} + _so, _x.{p.cx_manifest}.{p.mf_iter})",
        f"    _b = {p.fn_lookup_backend}(_x.{p.cx_manifest}.{p.mf_format})",
        f"    _x.{p.cx_middle} = _b.{p.cipher_method}(_to, _x.{p.cx_key1})",
        f"@{p.fn_reg_stage}({p.enum_stage}.{p.em_stage_inner})",
        f"def {p.fn_stage_inner}(_x: {p.cls_context}) -> None:",
        f"    if _x.{p.cx_middle} is None or _x.{p.cx_pass} is None: raise {p.exc_base}('m/p')",
        f"    _si = _x.{p.cx_middle}[:_x.{p.cx_manifest}.{p.mf_salt_size}]",
        f"    _ti = _x.{p.cx_middle}[_x.{p.cx_manifest}.{p.mf_salt_size}:]",
        f"    _g = {p.fn_lookup_kdf}(_x.{p.cx_manifest}.{p.mf_kdf})",
        f"    _x.{p.cx_key2} = _g(_x.{p.cx_pass}, {p.var_binding} + {p.prefix_inner_var} + _si, _x.{p.cx_manifest}.{p.mf_iter})",
        f"    _b = {p.fn_lookup_backend}(_x.{p.cx_manifest}.{p.mf_format})",
        f"    _x.{p.cx_plain} = _b.{p.cipher_method}(_ti, _x.{p.cx_key2})",
        f"@{p.fn_reg_stage}({p.enum_stage}.{p.em_stage_decomp})",
        f"def {p.fn_stage_decomp}(_x: {p.cls_context}) -> None:",
        f"    if _x.{p.cx_plain} is None: raise {p.exc_base}('q')",
        f"    if _x.{p.cx_manifest}.{p.mf_format} is {p.enum_fmt}.{p.em_fmt_zlib}: _x.{p.cx_plain} = zlib.decompress(_x.{p.cx_plain})",
    ])


def _emit_pipeline_runner(p):
    return "\n".join([
        f"{p.var_default_pipeline}: typing.Tuple[{p.enum_stage}, ...] = ({p.enum_stage}.{p.em_stage_decode}, {p.enum_stage}.{p.em_stage_outer}, {p.enum_stage}.{p.em_stage_inner}, {p.enum_stage}.{p.em_stage_decomp})",
        f"def {p.fn_run}(_x: {p.cls_context}, _st: typing.Sequence[{p.enum_stage}] = {p.var_default_pipeline}) -> bytes:",
        f"    for _s in _st:",
        f"        _r = {p.reg_stage}.get(_s)",
        f"        if _r is None: raise {p.exc_manifest}('runner {{0}}'.format(int(_s)))",
        f"        _r(_x)",
        f"    if _x.{p.cx_plain} is None: raise {p.exc_base}('q')",
        f"    return _x.{p.cx_plain}",
    ])


def _emit_execution_helpers(p):
    return "\n".join([
        f"def {p.fn_namespace}():",
        f"    _n: typing.Dict[str, typing.Any] = {{'__name__': __name__, '__builtins__': __builtins__, '__package__': globals().get('__package__')}}",
        f"    _n['__file__'] = __file__ if '__file__' in globals() else {p.cls_bundle}.{p.bundle_manifest_attr}.{p.mf_source}",
        f"    return _n",
        f"def {p.fn_materialize}(_p: bytes, _m: {p.cls_manifest}):",
        f"    if _m.{p.mf_bytecode}:",
        f"        import marshal",
        f"        return marshal.loads(_p)",
        f"    _w = io.TextIOWrapper(io.BytesIO(_p), encoding='utf-8')",
        f"    try: _t = _w.read()",
        f"    finally: _w.close()",
        f"    return compile(_t, _m.{p.mf_source}, 'exec')",
        f"def {p.fn_execute}(_p: bytes, _m: {p.cls_manifest}) -> None: exec({p.fn_materialize}(_p, _m), {p.fn_namespace}())",
    ])


def _emit_binding(p):
    parts = " + ".join(f"{fn}.__code__.co_code" for fn in [p.fn_execute, p.fn_materialize, p.fn_stage_outer, p.fn_stage_inner, p.fn_compute_binding])
    return "\n".join([
        f"def {p.fn_compute_binding}() -> bytes:",
        f"    return hashlib.sha256({parts}).digest()",
        f"{p.var_binding} = {p.fn_compute_binding}()",
    ])


def _emit_cli_helpers(p):
    return "\n".join([
        f"def {p.fn_parse_args}(_av):",
        f"    _p = argparse.ArgumentParser()",
        f"    _p.add_argument('--info', action='store_true')",
        f"    _p.add_argument('--verbose', action='store_true')",
        f"    _p.add_argument('--strict', action='store_true')",
        f"    return _p.parse_known_args(list(_av))[0]",
        f"def {p.fn_config_log}(_v: bool) -> None: logging.basicConfig(level=logging.DEBUG if _v else logging.WARNING, format={p.log_format_var})",
        f"def {p.fn_strict}(_m: {p.cls_manifest}) -> None:",
        f"    _e = {p.cls_bundle}.{p.bundle_manifest_attr}.{p.mf_version}",
        f"    if _m.{p.mf_version} != _e: raise {p.exc_manifest}('v {{0}}!={{1}}'.format(_m.{p.mf_version}, _e))",
    ])


def _emit_main(p):
    return "\n".join([
        f"def main(_av=None) -> int:",
        f"    _a = {p.fn_parse_args}(_av if _av is not None else sys.argv[1:]); {p.fn_config_log}(_a.verbose)",
        f"    if _a.info: print('\\n'.join({p.cls_bundle}.{p.bundle_manifest_attr}.{p.mf_method_lines}())); return 0",
        f"    try:",
        f"        if _a.strict: {p.fn_strict}({p.cls_bundle}.{p.bundle_manifest_attr})",
        f"        _x = {p.cls_bundle}.{p.bundle_method}(); _x.{p.cx_pass} = {p.fn_resolve_pass}(); _pt = {p.fn_run}(_x)",
        f"    except {p.exc_base} as _e:",
        f"        {p.logger_var}.error('%s', _e); sys.stderr.write('rb: {{0}}\\n'.format(_e)); return 2",
        f"    except SystemExit: raise",
        f"    except Exception as _e:",
        f"        {p.logger_var}.exception('%s', _e); return 2",
        f"    {p.fn_execute}(_pt, {p.cls_bundle}.{p.bundle_manifest_attr}); return 0",
        f"if __name__ == '__main__': raise SystemExit(main())",
    ])


def render_loader(payload, source_name, password_value, profile):
    p = profile
    parts = [
        "from __future__ import annotations",
        "import argparse, base64, dataclasses, enum, functools, hashlib, io, logging, os, sys, typing, zlib",
        "from cryptography.fernet import Fernet, InvalidToken",
        f"{p.logger_var} = logging.getLogger({p.logger_name!r}); {p.log_format_var} = {p.log_format!r}",
        _emit_exceptions(p),
        _emit_enums(p),
        _emit_dataclasses(p),
        _emit_codec_registry(p),
        _emit_kdf_registry(p),
        _emit_cipher_backend(p),
        _emit_prefix_bytes(p),
        _emit_bundle_class(p, payload, source_name),
        _emit_password_resolver(p, password_value),
        _emit_stage_registry_decorator(p),
        _emit_stages(p),
        _emit_pipeline_runner(p),
        _emit_execution_helpers(p),
        _emit_binding(p),
        _emit_cli_helpers(p),
        _emit_main(p),
    ]
    return "\n".join(parts) + "\n"


def _extract_binding(loader_source, profile):
    name = "__claudfuscator_build__"
    stub = ModuleType(name)
    stub.__name__ = name
    sys.modules[name] = stub
    ns = stub.__dict__
    ns["__name__"] = name
    try:
        exec(compile(loader_source, "<build>", "exec"), ns)
        value = ns.get(profile.var_binding)
    finally:
        sys.modules.pop(name, None)
    if not isinstance(value, (bytes, bytearray)):
        raise RuntimeError("binding extraction failed")
    return bytes(value)


def obfuscate(source_text, source_name):
    source = strip_docstrings(source_text)
    compressed = zlib.compress(source.encode("utf-8"), 9)
    p = new_polymorph()
    inner_prefix = bytes([p.prefix_inner_val])
    outer_prefix = bytes([p.prefix_outer_val])
    password = secrets.token_urlsafe(24)
    placeholder = render_loader(b"", source_name, password, p)
    binding = _extract_binding(placeholder, p)
    encrypted = encrypt(compressed, password.encode("utf-8"), p.pbkdf2_iterations, inner_prefix, outer_prefix, binding)
    return render_loader(encrypted, source_name, password, p)


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: crypt.py inputfile.py\n")
        return 2
    input_path = Path(sys.argv[1])
    if not input_path.is_file():
        sys.stderr.write(f"crypt.py: not a file: {input_path}\n")
        return 2
    output_path = input_path.with_name(input_path.stem + "_obf.py")
    source = input_path.read_text(encoding="utf-8")
    loader = obfuscate(source, input_path.name)
    output_path.write_text(loader, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
