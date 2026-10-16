from pathlib import Path

from app.modules.material.local_ocr import match_fields, reading_lines
from app.modules.material.ocr import DOCUMENT_FIELDS


def test_local_fields_handle_separate_labels_dates_and_identity():
    lines = [(text, 0.98) for text in [
        "统一社会信用代码", "91310000MA12345678", "名 称", "示例科技有限公司",
        "类 型有限责任公司", "成立日期2020年2月29日", "住 所上海市示例路1号", "经营范围技术服务",
    ]]
    fields = {item['target_field']: item['value'] for item in match_fields(lines, DOCUMENT_FIELDS['business_license'])}
    assert fields == dict(company_name='示例科技有限公司', company_type='有限责任公司',
                          register_number='91310000MA12345678', established_date='2020-02-29',
                          register_address='上海市示例路1号')
    identity = match_fields([(text, 0.95) for text in ["姓名张三", "性别男民族汉", "公民身份号码110101199001011234"]], DOCUMENT_FIELDS['id_card_front'])
    assert {item['target_field']: item['value'] for item in identity} == {
        'name_cn': '张三', 'gender': 'MALE', 'certificate_number': '110101199001011234',
    }


def test_local_invalid_date_and_missing_fields_not_fabricated():
    fields = match_fields([('成立日期2023年2月30日', 0.9)], DOCUMENT_FIELDS['business_license'])
    assert fields == []


def test_local_fullwidth_and_field_specific_scores():
    lines = [('名称示例科技有限公司', 0.99), ('类型有限责任公司', 0.97),
             ('成立日期２０２０年０２月２９日', 0.98), ('登记机关模糊文字', 0.51)]
    fields = {item['target_field']: item for item in match_fields(lines, DOCUMENT_FIELDS['business_license'])}
    assert fields['company_name']['confidence'] == 0.99
    assert fields['established_date']['value'] == '2020-02-29'
    assert fields['established_date']['confidence'] == 0.98


def test_number_elsewhere_is_not_assigned_without_label():
    assert match_fields([('无关编号91310000MA12345678', 0.99)], DOCUMENT_FIELDS['business_license']) == []


def test_distant_unlabelled_column_does_not_pollute_company_name():
    from types import SimpleNamespace
    result = SimpleNamespace(
        txts=['名称示例科技有限公司', '与公司名称无关的右栏文字'], scores=[0.99, 0.95],
        boxes=[[[0, 0], [180, 0], [180, 20], [0, 20]],
               [[500, 0], [700, 0], [700, 20], [500, 20]]],
    )
    fields = match_fields(reading_lines(result), DOCUMENT_FIELDS['business_license'])
    assert fields[0]['value'] == '示例科技有限公司'


def login(client):
    response = client.post("/api/auth/login", json={"account": "demo@eprflow.com", "password": "Demo123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_recognize_uploaded_document_returns_form_field_matches(client, monkeypatch):
    headers = login(client)
    monkeypatch.setattr("app.modules.material.router.stored_file", lambda _url, _token: Path("license.png"))
    monkeypatch.setattr(
        "app.modules.material.router.recognize_document",
        lambda source, document_type: ([{
            "target_field": "company_name",
            "label": "公司中文名称",
            "value": "示例科技有限公司",
            "confidence": 0.98,
        }], ["请核对注册地址"]),
    )

    response = client.post("/api/files/recognize", headers=headers, json={
        "file_url": "/files/license.png",
        "recognition_token": "x" * 64,
        "document_type": "business_license",
    })

    assert response.status_code == 200
    assert response.json()["fields"][0]["target_field"] == "company_name"
    assert response.json()["fields"][0]["value"] == "示例科技有限公司"
    assert response.json()["warnings"] == ["请核对注册地址"]


def test_recognize_requires_login_and_known_document_type(client):
    unauthorized = client.post("/api/files/recognize", json={
        "file_url": "/files/license.png",
        "recognition_token": "x" * 64,
        "document_type": "business_license",
    })
    assert unauthorized.status_code == 401

    invalid = client.post("/api/files/recognize", headers=login(client), json={
        "file_url": "/files/license.png",
        "recognition_token": "x" * 64,
        "document_type": "unknown",
    })
    assert invalid.status_code == 422
