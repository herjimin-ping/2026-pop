import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="지역별 연령별 인구 구조", layout="wide")

# -----------------------------
# 데이터 파일 (app.py와 같은 폴더에 있다고 가정)
# -----------------------------
DATA_FILE = Path(__file__).parent / "202606_202606_연령별인구현황_월간.csv"


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """행정안전부 '연령별 인구현황' 원본 CSV를 읽어옵니다.
    보통 EUC-KR(cp949) 인코딩으로 배포되므로 순서대로 시도합니다.
    """
    last_err = None
    for enc in ["cp949", "euc-kr", "utf-8-sig", "utf-8"]:
        try:
            return pd.read_csv(path, encoding=enc, thousands=",")
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    raise ValueError(f"CSV 인코딩을 인식하지 못했습니다 (cp949 / utf-8 확인). {last_err}")


def clean_region_name(raw: str) -> str:
    """'서울특별시 종로구 (1111000000)' -> '서울특별시 종로구'"""
    return re.sub(r"\s*\(\d+\)\s*$", "", str(raw)).strip()


@st.cache_data
def parse_age_columns(columns):
    """'2026년06월_계_0세' 같은 컬럼명에서 (기준월, 성별, 나이) 정보를 추출합니다."""
    pattern = re.compile(r"^(\d{4}년\d{2}월)_(계|남|여)_(\d+세|\d+세 이상)$")

    parsed = []
    for col in columns:
        m = pattern.match(col)
        if not m:
            continue
        yyyymm, gender, age_label = m.groups()
        if age_label.endswith("이상"):
            age_num, age_display = 101, "100세 이상"
        else:
            n = int(age_label.replace("세", ""))
            age_num, age_display = n, f"{n}세"
        parsed.append(
            {
                "column": col,
                "yyyymm": yyyymm,
                "gender": gender,
                "age_num": age_num,
                "age_display": age_display,
            }
        )
    return pd.DataFrame(parsed)


# -----------------------------
# 데이터 로드
# -----------------------------
if not DATA_FILE.exists():
    st.title("👥 지역별 연령별 인구 구조")
    st.error(
        f"데이터 파일을 찾을 수 없습니다: '{DATA_FILE.name}'\n\n"
        "app.py와 같은 폴더에 원본 CSV 파일을 이름 그대로 올려주세요."
    )
    st.stop()

df = load_data(DATA_FILE)
df["행정구역_정리"] = df["행정구역"].apply(clean_region_name)

age_info = parse_age_columns(df.columns)
if age_info.empty:
    st.error("CSV에서 연령별 인구 컬럼을 찾지 못했습니다. 파일 형식을 확인해주세요.")
    st.stop()

available_yyyymm = sorted(age_info["yyyymm"].unique())
available_genders = sorted(
    age_info["gender"].unique(), key=lambda g: {"계": 0, "남": 1, "여": 2}.get(g, 9)
)
gender_label = {"계": "전체", "남": "남자", "여": "여자"}

# -----------------------------
# 사이드바: 조회 옵션
# -----------------------------
st.sidebar.header("🔎 조회 옵션")

yyyymm_sel = st.sidebar.selectbox("기준 연월", available_yyyymm, index=len(available_yyyymm) - 1)
gender_sel = st.sidebar.radio(
    "성별", available_genders, format_func=lambda g: gender_label.get(g, g), horizontal=True
)

region_options = sorted(df["행정구역
