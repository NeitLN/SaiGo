"""Lỗi kiểm tra request (422) bằng tiếng Việt và không bao giờ thành 500 (test lại 15/11, P-1, P-5).

Handler mặc định của FastAPI chép nguyên `input` vào response; khi body có NaN, Infinity hay 1e400, giá trị đó
không ghi được ra JSON chuẩn nên request thành lỗi 500. Ở đây giữ cấu trúc danh sách lỗi của Pydantic (`type`,
`loc`, `msg`, `ctx`), thay `msg` bằng câu tiếng Việt có tên trường, bỏ tiền tố "Value error, ", và đổi mọi số
không hữu hạn trong `input`/`ctx` thành chuỗi.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _plain(x: Any) -> Any:
    """Bản ghi được ra JSON chuẩn: số không hữu hạn thành chuỗi, ngoại lệ trong ctx thành chuỗi."""
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    return str(x)


def _message(err: dict[str, Any]) -> str:
    t = err.get("type", "")
    ctx = err.get("ctx") or {}
    if t == "missing":
        return "thiếu trường bắt buộc"
    if t in ("float_parsing", "float_type"):
        return "phải là số"
    if t in ("int_parsing", "int_type", "int_from_float"):
        return "phải là số nguyên"
    if t in ("bool_parsing", "bool_type"):
        return "phải là true hoặc false"
    if t in ("string_type", "string_unicode"):
        return "phải là chuỗi"
    if t == "list_type":
        return "phải là danh sách"
    if t in ("model_type", "model_attributes_type", "dict_type"):
        return "phải là object"
    if t == "finite_number":
        return "phải là số hữu hạn"
    if t == "greater_than_equal":
        return f"phải lớn hơn hoặc bằng {ctx.get('ge')}"
    if t == "less_than_equal":
        return f"phải nhỏ hơn hoặc bằng {ctx.get('le')}"
    if t == "too_short":
        return f"cần ít nhất {ctx.get('min_length')} phần tử"
    if t == "too_long":
        return f"tối đa {ctx.get('max_length')} phần tử"
    if t == "string_too_short":
        return f"cần ít nhất {ctx.get('min_length')} ký tự"
    if t == "string_too_long":
        return f"tối đa {ctx.get('max_length')} ký tự"
    if t == "json_invalid":
        return "JSON không hợp lệ"
    msg = str(err.get("msg", ""))
    # Lỗi từ validator của schema đã viết tiếng Việt; Pydantic thêm tiền tố "Value error, " / "Assertion failed, ".
    for prefix in ("Value error, ", "Assertion failed, "):
        if msg.startswith(prefix):
            return msg[len(prefix):]
    return msg


def _where(loc: Any) -> str:
    parts = [str(p) for p in (loc or []) if p not in ("body", "query", "path")]
    return ".".join(parts)


def translate(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for err in errors:
        where = _where(err.get("loc"))
        text = _message(err)
        item = {k: v for k, v in err.items() if k in ("type", "loc", "input", "ctx")}
        item["msg"] = f"{where}: {text}" if where else text
        out.append(_plain(item))
    return out


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": translate(list(exc.errors()))})
