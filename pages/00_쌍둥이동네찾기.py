import re
import glob

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------
# 기본 설정
# ----------------------------------------------------------
st.set_page_config(
    page_title="행정동별 1인세대 인구구조",
    page_icon="📊",
    layout="wide",
)

st.title("📊 행정동별 성연령별 1인세대수 인구구조")
st.caption("행정안전부 주민등록 인구통계(1인세대) 데이터를 기반으로 지역별 연령대 분포를 확인합니다.")


# ----------------------------------------------------------
# 데이터 로드 함수
# ----------------------------------------------------------
@st.cache_data
def load_data(file) -> pd.DataFrame:
    """CSV(cp949 인코딩, 천단위 콤마 포함)를 읽어 정제된 DataFrame으로 반환."""
    df = pd.read_csv(file, encoding="cp949")

    parsed = df["행정구역"].str.extract(r"^(.*?)\s*\((\d+)\)\s*$")
    df["지역명"] = parsed[0].str.strip()
    df["행정코드"] = parsed[1]

    num_cols = [c for c in df.columns if c not in ("행정구역", "지역명", "행정코드")]
    for c in num_cols:
        df[c] = (
            df[c].astype(str).str.replace(",", "", regex=False).replace("", "0").astype(int)
        )

    return df


def find_default_csv():
    candidates = glob.glob("*행정동*세대수*월간.csv") + glob.glob("*.csv")
    return candidates[0] if candidates else None


def get_year_month_prefix(columns) -> str:
    for c in columns:
        m = re.match(r"^(\d{4}년\d{2}월)_", c)
        if m:
            return m.group(1)
    return ""


AGE_GROUPS = [
    "0~9세", "10~19세", "20~29세", "30~39세", "40~49세",
    "50~59세", "60~69세", "70~79세", "80~89세", "90~99세", "100세 이상",
]


default_csv = find_default_csv()

with st.sidebar:
    st.header("⚙️ 데이터 불러오기")
    uploaded = st.file_uploader("CSV 파일 업로드 (선택)", type=["csv"])

data_source = uploaded if uploaded is not None else default_csv

if data_source is None:
    st.warning("CSV 파일을 찾을 수 없습니다. 왼쪽 사이드바에서 파일을 업로드해 주세요.")
    st.stop()

df = load_data(data_source)
prefix = get_year_month_prefix(df.columns)

st.sidebar.header("🔍 지역 선택")

df["단위"] = df["지역명"].apply(
    lambda x: {1: "전국/시도", 2: "시군구", 3: "행정동"}.get(len(x.split()), "행정동")
)
df.loc[df["지역명"] == "전국", "단위"] = "전국"

level = st.sidebar.radio(
    "행정구역 단위",
    ["행정동", "시군구", "시도", "전국"],
    index=0,
    horizontal=False,
)

level_map = {"행정동": "행정동", "시군구": "시군구", "시도": "전국/시도", "전국": "전국"}
level_df = df[df["단위"] == level_map[level]].copy()

if level in ("행정동", "시군구"):
    sido_options = sorted(level_df["지역명"].str.split().str[0].unique())
    sido_pick = st.sidebar.selectbox("시/도 필터 (선택)", ["전체"] + sido_options)
    if sido_pick != "전체":
        level_df = level_df[level_df["지역명"].str.startswith(sido_pick)]

region_options = sorted(level_df["지역명"].unique())

selected_region = st.sidebar.selectbox(
    "지역명을 선택하거나 입력(검색)하세요",
    region_options,
    index=0 if region_options else None,
    placeholder="예: 종로구, 청운효자동 ...",
)

if not selected_region:
    st.info("왼쪽에서 지역을 선택해 주세요.")
    st.stop()

row = df[df["지역명"] == selected_region].iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("선택 지역", selected_region)
col2.metric("총 1인세대수(계)", f"{row[f'{prefix}_계_총세대수']:,}")
col3.metric("남 / 여", f"{row[f'{prefix}_남_총세대수']:,} / {row[f'{prefix}_여_총세대수']:,}")

st.divider()

st.subheader(f"📈 {selected_region} 연령대별 1인세대수")

male_vals = [row[f"{prefix}_남_{g}"] for g in AGE_GROUPS]
female_vals = [row[f"{prefix}_여_{g}"] for g in AGE_GROUPS]
total_vals = [row[f"{prefix}_계_{g}"] for g in AGE_GROUPS]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=AGE_GROUPS, y=total_vals, mode="lines+markers", name="계",
    line=dict(width=3), marker=dict(size=7),
))
fig.add_trace(go.Scatter(
    x=AGE_GROUPS, y=male_vals, mode="lines+markers", name="남",
    line=dict(width=2, dash="dash"), marker=dict(size=6),
))
fig.add_trace(go.Scatter(
    x=AGE_GROUPS, y=female_vals, mode="lines+markers", name="여",
    line=dict(width=2, dash="dot"), marker=dict(size=6),
))

fig.update_layout(
    xaxis_title="연령대",
    yaxis_title="1인세대수(세대)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=520,
    margin=dict(l=10, r=10, t=40, b=10),
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("📋 원본 수치 표 보기"):
    table = pd.DataFrame({"연령대": AGE_GROUPS, "계": total_vals, "남": male_vals, "여": female_vals})
    st.dataframe(table, use_container_width=True, hide_index=True)

st.caption(f"데이터 기준월: {prefix}  |  출처: 행정안전부 주민등록 인구통계")
