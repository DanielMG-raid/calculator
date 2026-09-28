import streamlit as st
import math
from dataclasses import dataclass
from typing import Dict, List, Optional

# ============================
# 1. 캐릭터 DB 및 기본 정의
# ============================
COLOR_MATCH_BONUS = 0.30

@dataclass(frozen=True)
class Character:
    name: str
    base_damage: int
    hits: int
    crit_rate: float
    crit_bonus: float
    mp_cost: int
    color: str
    party_damage_buff: float = 0.0
    lepain_crit_buff: float = 0.0

    def expected_damage(
        self,
        common_damage_buff: float,
        party_damage_buff_total: float,
        lepain_crit_buff_total: float,
        stone_crit_buff: float,
        weakness_colors: List[str],
        weakness_bonus_by_color: Dict[str, float],
    ) -> float:
        base = self.base_damage * self.hits
        dmg_mult = 1.0 + common_damage_buff + party_damage_buff_total

        if self.color in weakness_colors:
            dmg_mult += COLOR_MATCH_BONUS

        dmg_mult += weakness_bonus_by_color.get(self.color, 0.0)
        if dmg_mult < 0:
            dmg_mult = 0.0

        if self.crit_rate <= 0:
            return base * dmg_mult

        crit_mult = 1.0 + self.crit_bonus + lepain_crit_buff_total + stone_crit_buff
        expected_mult = (1.0 - self.crit_rate) + self.crit_rate * crit_mult
        return base * expected_mult * dmg_mult

CHARACTER_DB: Dict[str, Character] = {
    "눈설탕": Character("눈설탕", 5640000, 5, 0.0, 0.0, 370, color="파랑"),
    "캡틴아이스": Character("캡틴아이스", 2025000, 12, 0.25, 0.30, 400, color="파랑", party_damage_buff=0.13),
    "스네이크": Character("스네이크", 3400000, 8, 0.0, 0.0, 380, color="노랑"),
    "인삼": Character("인삼", 7465000, 3, 0.0, 0.0, 280, color="빨강"),
    "비트": Character("비트", 1807500, 15, 0.20, 0.30, 400, color="빨강"),
    "레판": Character("레판", 8320000, 3, 0.20, 0.30, 400, color="빨강", lepain_crit_buff=0.35),
    "뱀파": Character("뱀파", 4462500, 4, 0.0, 0.0, 340, color="빨강"),
}

CHARACTER_ALIAS: Dict[str, str] = {
    "눈설": "눈설탕", "눈설탕": "눈설탕", "눈": "눈설탕",
    "캡아": "캡틴아이스", "캡틴": "캡틴아이스", "캡틴아이스": "캡틴아이스", "캡": "캡틴아이스",
    "스네": "스네이크", "스네이크": "스네이크", "스": "스네이크",
    "인삼": "인삼", "인": "인삼",
    "비트": "비트", "비": "비트",
    "레판": "레판", "레": "레판",
    "뱀파": "뱀파", "뱀": "뱀파",
}

def build_party_from_text(text: str) -> List[Character]:
    tokens = text.split()
    if len(tokens) % 2 != 0:
        raise ValueError("파티 구성은 '이름 수량' 쌍이어야 합니다. 예) 비트 3 레판 1")
    party: List[Character] = []
    for i in range(0, len(tokens), 2):
        raw_name = tokens[i]
        count = int(tokens[i + 1])
        if raw_name not in CHARACTER_ALIAS:
            raise KeyError(f"알 수 없는 캐릭터: {raw_name}")
        name = CHARACTER_ALIAS[raw_name]
        if count > 0:
            party.extend([CHARACTER_DB[name]] * count)
    return party

# ============================
# 2. 핵심 계산 함수
# ============================
def calculate_party(
    party: List[Character],
    common_damage_buff: float,
    stone_crit_buff: float,
    weakness_colors: List[str],
    weakness_bonus_by_color: Dict[str, float],
    energy_decrease_by_color: Dict[str, float],
):
    party_damage_buff_total = max((c.party_damage_buff for c in party), default=0.0)
    lepain_crit_buff_total = max((c.lepain_crit_buff for c in party), default=0.0)

    total_damage = 0.0
    total_mp = 0
    total_dmg_per_mp_sum = 0.0

    for c in party:
        dmg = c.expected_damage(
            common_damage_buff=common_damage_buff,
            party_damage_buff_total=party_damage_buff_total,
            lepain_crit_buff_total=lepain_crit_buff_total,
            stone_crit_buff=stone_crit_buff,
            weakness_colors=weakness_colors,
            weakness_bonus_by_color=weakness_bonus_by_color,
        )
        total_damage += dmg

        mp_mult = 1.0 + energy_decrease_by_color.get(c.color, 0.0)
        mp_mult = max(0.0, mp_mult)
        effective_mp = int(math.ceil(c.mp_cost * mp_mult)) if c.mp_cost > 0 else 0

        total_mp += effective_mp
        dmg_per_mp = (dmg / effective_mp) if effective_mp > 0 else 0.0
        total_dmg_per_mp_sum += dmg_per_mp

    return total_damage, total_dmg_per_mp_sum, total_mp

# ============================
# 3. Streamlit UI
# ============================
st.set_page_config(page_title="사마귀 보스 계산기", page_icon="🧮")
st.title("🧮 사마귀 레이드 계산기")

# 1. 파티 구성
st.subheader("1. 파티 구성")
party_text = st.text_input("파티 입력 (예: 비트 3 레판 1 / 스네 4 캡아 1)", value="비트 3 레판 1")

# 2. 버프 및 소환석 옵션
st.subheader("2. 버프 및 소환석 옵션")
col1, col2 = st.columns(2)
with col1:
    common_buff_pct = st.number_input("공통 피해 증가 (%)", value=0.0, step=1.0)
    stone_crit_pct = st.number_input("치명타 피해 증가 (%)", value=0.0, step=1.0)
with col2:
    game_speed_pct = st.number_input("게임속도 증가 (%)", value=0.0, step=1.0)
    energy_drop_on = st.checkbox("⚡ 스킬 에너지 많이 떨어짐 (스많떨)", value=True)

# 약점 색상 및 추가 옵션
st.markdown("##### 보스 약점 및 색상별 옵션")
selected_weakness_colors = st.multiselect(
    "🎯 보스 약점 색상 선택 (해당 색상 스킬 딜 +30% 합연산)",
    options=["빨강", "노랑", "파랑"],
    default=["빨강"]
)

col_c1, col_c2, col_c3 = st.columns(3)
colors = ["빨강", "노랑", "파랑"]
weakness_bonus = {}
energy_decrease = {}

for idx, col in enumerate([col_c1, col_c2, col_c3]):
    c_name = colors[idx]
    with col:
        st.caption(f"**{c_name}**")
        w_pct = st.number_input(f"{c_name} 추가 피해(%)", value=0.0, key=f"w_{c_name}")
        e_pct = st.number_input(f"{c_name} 에너지 증감(%) (+:감소, -:증가)", value=0.0, key=f"e_{c_name}")
        if w_pct != 0: weakness_bonus[c_name] = w_pct / 100.0
        if e_pct != 0: energy_decrease[c_name] = e_pct / 100.0

st.divider()

# 3. 보스 설정 (맨 밑 배치)
st.subheader("3. 보스 설정 및 계산")
boss_hp = st.number_input("🎯 보스 체력", min_value=1.0, value=10_000_000_000.0, step=100_000_000.0, format="%.0f")

if st.button("🚀 계산하기", type="primary"):
    try:
        party = build_party_from_text(party_text)
        
        # 1. 파티 딜 및 딜효율(P) 계산
        total_dmg, total_dmg_per_mp_sum, total_mp = calculate_party(
            party=party,
            common_damage_buff=common_buff_pct / 100.0,
            stone_crit_buff=stone_crit_pct / 100.0,
            weakness_colors=selected_weakness_colors,
            weakness_bonus_by_color=weakness_bonus,
            energy_decrease_by_color=energy_decrease
        )
        
        # 2. 게임속도 반영한 최종 딜효율 계산
        game_speed_mult = 1.0 + (game_speed_pct / 100.0)
        effective_dps_efficiency = total_dmg_per_mp_sum * game_speed_mult
        
        # 3. 보스체력 / (딜효율 * 게임속도) 수치 계산
        clear_judge_value = boss_hp / effective_dps_efficiency if effective_dps_efficiency > 0 else float("inf")
        
        st.divider()
        st.markdown("### 📊 계산 결과")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("1사이클 총 피해량", f"{total_dmg:,.0f}")
        m2.metric("기본 딜효율 (P)", f"{total_dmg_per_mp_sum:,.2f}")
        m3.metric("게임속도 적용 딜효율", f"{effective_dps_efficiency:,.2f}")

        # 4. 클리어 경계선 판정 (스많떨 ON: 9900 / OFF: 8700)
        st.markdown("### 🎯 클리어 여부 판정")
        threshold = 9900.0 if energy_drop_on else 8700.0
        
        if clear_judge_value < threshold:
            margin = ((threshold - clear_judge_value) / threshold) * 100
            st.success(f"✅ **클리어 가능!** (**{margin:.1f}%** 여유)")
        else:
            margin = ((clear_judge_value - threshold) / threshold) * 100
            st.error(f"❌ **클리어 어려움** (**{margin:.1f}%** 부족)")
        
    except Exception as e:
        st.error(f"계산 중 오류가 발생했습니다: {e}")

# ============================
# 맨 밑 하단 옅은 문구
# ============================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888888; font-size: 12px; margin-top: 20px;">
        오늘컨별로네님 바쁘신 관계로 임시 가동 중
    </div>
    """,
    unsafe_allow_html=True
)
