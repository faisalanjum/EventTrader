# The approved reader calls. Copied from the frozen scripts (prepare_work, real575_20261005): the free OCR settings of run_free_rows.py with
# free_runner.py's failure record; Chandra's call from mac/mac_real.py. Each reader takes a picture's bytes and comes with the settings it
# actually runs with (the identity of its readings, computed once) and a status rule that also checks its reading's shape; worker.py
# keeps the readings. PP-OCR and OnnxTR are separate readers, so one tool's good reading is never redone or lost with the other's failure.
# Undecodable bytes or unprepared transparency are a PictureError; source-rendered inputs must be opaque. A storage failure is never caught here. The optional Sonnet caller
# stays outside the runtime until it is production-safe (Codex r12 C3).
import ast, functools, hashlib, importlib.metadata as md, inspect, io, json, math, os, re, tempfile, textwrap, time, types, zipfile
from pathlib import PurePath
from ..get.acquire import StorageError

OX = dict(det_arch='fast_base', reco_arch='parseq', load_in_8_bit=False)
MAX_TOKENS = 12384                                                       # Chandra's output limit (routing's 'cut off' reads it)


class PictureError(ValueError):
    """The supplied picture cannot be read as-is: invalid image content or transparency needing its source background."""


def _image(data):  # the picture decoded from its bytes in memory, so any failure here is the picture's own - except running out of memory
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data)); im.load()
        if im.has_transparency_data and im.convert('RGBA').getchannel('A').getextrema() != (255, 255):
            raise ValueError('non-opaque image requires source-context rendering before OCR')
        return im.convert('RGB')
    except MemoryError: raise                                            # the machine, not the picture: stop (as the converter does)
    except Exception as e: raise PictureError(f'{type(e).__name__}: {str(e)[:200]}') from e


@functools.cache
def _free_tools():  # PP-OCRv6 medium (RapidOCR 3.9.2) and OnnxTR fast_base+parseq, loaded once, with the settings each is built with
    import cv2, onnxruntime as ort
    from omegaconf import OmegaConf
    from rapidocr import RapidOCR
    from rapidocr.utils.typings import OCRVersion, ModelType
    from onnxtr.models import ocr_predictor, EngineConfig
    params = {'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6,
              'Rec.model_type': ModelType.MEDIUM, 'Global.use_cls': False, 'EngineConfig.onnxruntime.intra_op_num_threads': 6}
    rcfg = RapidOCR._load_config(RapidOCR.__new__(RapidOCR), None, params)   # RapidOCR's own full configuration: its defaults with our params
    pp_tool = RapidOCR(params=params)
    weights = _pp_weights(pp_tool.cfg)                                    # verify after loading: its downloader does not check a fresh response
    so = ort.SessionOptions(); so.intra_op_num_threads = 6; so.inter_op_num_threads = 1; cfg = EngineConfig(session_options=so)
    versions = lambda *names: {n: md.version(n) for n in names}
    pp = dict(reader='pp-ocr', config=_plain(OmegaConf.to_container(rcfg, resolve=True, enum_to_str=True)), weights=weights, opencv=cv2.__version__,
              code=[_code_id(_image), _code_id(_pp_boxes)], versions=versions('rapidocr', 'onnxruntime', 'numpy', 'pillow'))
    ox_tool = ocr_predictor(**OX, det_engine_cfg=cfg, reco_engine_cfg=cfg)
    ox = dict(reader='onnxtr', args=OX, threads=[so.intra_op_num_threads, so.inter_op_num_threads], models=_ox_models(ox_tool),
              code=[_code_id(_image), _code_id(_ox_boxes)], versions=versions('onnxtr', 'onnxruntime', 'numpy', 'pillow'))
    return pp_tool, ox_tool, dict(pp=pp, ox=ox)


def _ox_models(predictor):  # the model files OnnxTR loaded, by full SHA-256 (its loader checks only the 8-hex prefix in the file name), and the
    return {k: dict(sha256=_file_sha256(m.model_path), providers=m.runtime.get_providers())   # providers registered for each session, in order
            for k, m in (('det', predictor.det_predictor.model), ('reco', predictor.reco_predictor.model))}


def _pp_weights(cfg):  # the exact default models selected by RapidOCR's configuration; verify once before any result can be kept
    from rapidocr.inference_engine.base import FileInfo, InferSession
    from rapidocr.utils.download_file import DownloadFile
    weights = {}
    for t in ('Det', 'Rec'):
        info = InferSession.get_model_url(FileInfo(**{k: cfg[t][k] for k in ('engine_type', 'ocr_version', 'task_type', 'lang_type', 'model_type')}))
        path = cfg[t].get('model_path') or os.path.join(cfg.Global.model_root_dir, os.path.basename(info['model_dir']))
        if not DownloadFile.check_file_sha256(path, info['SHA256']): raise ValueError(f'{t} model does not match its expected SHA-256: {path}')
        weights[t] = info['SHA256']
    return weights


def _plain(x):  # a configuration without machine locations (paths), so moving the same setup does not change its identity
    if isinstance(x, dict): return {k: _plain(v) for k, v in x.items() if not isinstance(v, PurePath)}
    return [_plain(v) for v in x] if isinstance(x, list) else x


def _pp_boxes(pp, im):  # PP-OCR's text lines with their boxes
    import numpy as np
    im = np.array(im)
    r = pp(im[:, :, ::-1].copy())
    return [dict(t=t, box=[round(float(v), 1) for v in np.array(b).reshape(-1)]) for t, b in zip(r.txts or (), r.boxes if r.boxes is not None else [])]


def _ox_boxes(ox, im):  # OnnxTR's words with their boxes
    import numpy as np
    W, H = im.size; doc = ox([np.array(im)])
    return [dict(t=w.value, box=[round(w.geometry[0][0] * W, 1), round(w.geometry[0][1] * H, 1), round(w.geometry[1][0] * W, 1), round(w.geometry[1][1] * H, 1)])
            for p in doc.pages for b in p.blocks for l in b.lines for w in l.words]


def free_ocr(picture):
    """Both free tools' text boxes with their positions (evidence only): dict(file, w, h, pp, ox, pp_secs, ox_secs), plus pp_error /
    ox_error naming a tool's inference failure (its boxes then empty). A storage or memory failure is not a tool failure: it stops."""
    pp, ox, _ = _free_tools()
    with open(picture, 'rb') as f: im = _image(f.read())
    rec = dict(file=os.path.basename(picture), w=im.width, h=im.height)
    for name, tool, boxes in (('pp', pp, _pp_boxes), ('ox', ox, _ox_boxes)):
        t0 = time.time()
        try: rec[name] = boxes(tool, im)
        except (OSError, StorageError, MemoryError): raise
        except Exception as e: rec[name] = []; rec[name + '_error'] = f'{type(e).__name__}: {str(e)[:200]}'
        rec[name + '_secs'] = round(time.time() - t0, 2)
    return rec


def _free_status(r):  # one free tool's reading: the picture's size and the tool's boxes
    if not (isinstance(r, dict) and set(r) == {'w', 'h', 'boxes'} and isinstance(r['boxes'], list)): raise ValueError('not a free OCR reading')
    if any(type(r[k]) is not int or r[k] <= 0 for k in ('w', 'h')): raise ValueError('invalid picture dimensions')
    for b in r['boxes']:
        if not (isinstance(b, dict) and isinstance(b.get('t'), str) and isinstance(b.get('box'), list)
                and len(b['box']) in (4, 8) and all(type(v) in (int, float) and math.isfinite(v) for v in b['box'])):
            raise ValueError('invalid free OCR text box')
    return 'complete'


def free_readers():  # PP-OCR and OnnxTR as two readers for worker.py: each kept, reused and retried on its own
    pp, ox, s = _free_tools()
    def reader(tool, boxes, settings):
        def read(data): im = _image(data); return dict(w=im.width, h=im.height, boxes=boxes(tool, im))
        return types.SimpleNamespace(read=read, settings=settings, status=_free_status)
    return reader(pp, _pp_boxes, s['pp']), reader(ox, _ox_boxes, s['ox'])


def free_record(pp, ox):  # the free OCR evidence the packets read, from the two tools' worker records of ONE picture's bytes; None when neither tool read it
    if not (isinstance(pp.get('image_sha256'), str) and pp['image_sha256'] and pp['image_sha256'] == ox.get('image_sha256')):  # the worker's own identity of the bytes read
        raise ValueError("the two free OCR records are not of one picture's bytes")                                           # (settings differ by design)
    rec = {}
    for name, r in (('pp', pp), ('ox', ox)):
        if r['status'] == 'error': rec[name] = []; rec[name + '_error'] = r['error']
        else:
            if 'w' in rec and (rec['w'], rec['h']) != (r['result']['w'], r['result']['h']): raise ValueError('the two free OCR readings measure the picture differently')  # one box frame
            rec[name] = r['result']['boxes']; rec.update(w=r['result']['w'], h=r['result']['h'])
    return rec if 'w' in rec else None


def _chandra_status(r):  # a Chandra reading: [raw HTML, run record]; 'cut off' when it stopped at its output limit
    if not (isinstance(r, list) and len(r) == 2 and isinstance(r[0], str) and isinstance(r[1], dict)): raise ValueError('not a Chandra reading')
    tokens = r[1].get('generation_tokens')
    if tokens is not None and (type(tokens) is not int or tokens < 0): raise ValueError('invalid generated-token count')
    return 'cut off' if (tokens or 0) >= MAX_TOKENS else 'complete'


def chandra(model, wheel):
    """Chandra OCR 2 on MLX (the Mac): read(picture bytes) -> [raw HTML, run record]. `model` is the MLX model folder (chandra-bf16), `wheel`
    the chandra_ocr 0.2.0 wheel, whose own picture sizing and ocr_layout prompt are used."""
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    from PIL import Image
    z = zipfile.ZipFile(wheel); ns = {}
    exec(z.read('chandra/model/util.py').decode(), ns)                       # Chandra's own picture sizing
    exec(z.read('chandra/prompts.py').decode().split('if __name__')[0], ns)  # Chandra's own prompts
    min_dim = int(re.search(r'MIN_IMAGE_DIM: int = (\d+)', z.read('chandra/settings.py').decode()).group(1))  # 1,536 in 0.2.0
    settings = dict(reader='chandra', model_files=_tree_sha256(model), wheel=_tree_sha256(wheel), max_tokens=MAX_TOKENS, temperature=0.0,
                    code=[_code_id(_image), _code_id(chandra)], versions={p: md.version(p) for p in ('mlx-vlm', 'mlx', 'transformers', 'tokenizers', 'pillow')})
    m, processor = load(model); config = load_config(model)
    def read(data):
        im = _image(data)
        if im.width < min_dim or im.height < min_dim:                    # chandra/input.py load_image: shorter side to min_dim
            s = min_dim / min(im.width, im.height); im = im.resize((int(im.width * s), int(im.height * s)), Image.Resampling.LANCZOS)
        with tempfile.TemporaryDirectory() as d:
            png = os.path.join(d, 'page.png'); ns['scale_to_fit'](im).save(png); t = time.time()
            r = generate(m, processor, apply_chat_template(processor, config, ns['PROMPT_MAPPING']['ocr_layout'], num_images=1), [png],
                         max_tokens=MAX_TOKENS, temperature=0.0, verbose=False)
        return [getattr(r, 'text', r), dict(secs=round(time.time() - t, 1), **{k: getattr(r, k, None) for k in ('prompt_tokens', 'generation_tokens', 'generation_tps', 'peak_memory')})]
    return types.SimpleNamespace(read=read, settings=settings, status=_chandra_status)


def _tree_sha256(path):  # the (relative name, file SHA-256) list of a model folder (or one file), hashed as one list; listing errors stop
    if not os.path.exists(path): raise FileNotFoundError(f'{path}: the reader settings name a local model folder or file')
    def stop(e): raise e
    files = [path] if os.path.isfile(path) else sorted(os.path.join(d, f) for d, _, fs in os.walk(path, onerror=stop) for f in fs)   # ponytail: reads every weight once per job (~1 min for 18 GB)
    return hashlib.sha256(json.dumps([[os.path.relpath(p, path), _file_sha256(p)] for p in files]).encode()).hexdigest()


def _file_sha256(path):  # one file's SHA-256, read in pieces
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
    return h.hexdigest()


def _code_id(fn):  # the reading code's own identity: its syntax tree without docstrings (comments and layout do not count)
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return hashlib.sha256(ast.dump(tree).encode()).hexdigest()
