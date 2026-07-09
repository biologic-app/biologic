"""seed the 5 real laboratories with research goals and indicators

The legacy .xls Бак/Т-Х/Т-Б/РВ/ПЦР mark columns map to 5 real laboratories by
code (BAK/TH/TB/RV/PCR). This migration seeds those labs, a handful of
representative research goals per lab (``research_goals.lab_id``) and indicators
linking each goal to the first five reference sample types
(SAMPLE-TYPE-001..005). That makes the "(sample type + laboratory) → research
goals" derivation return a non-empty result for common sample types.

Idempotent: every insert is guarded by ON CONFLICT / NOT EXISTS.

Revision ID: 20260709_0022
Revises: 20260709_0021
Create Date: 2026-07-09 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260709_0022"
down_revision = "20260709_0021"
branch_labels = None
depends_on = None

_GOAL_CODE_REGEX = "^RG-(BAK|TH|TB|RV|PCR)-[0-9]+$"


def upgrade() -> None:
    # 1. The 5 real laboratories, resolved from legacy mark columns by code.
    op.execute("""
        INSERT INTO labs (code, name, full_name)
        VALUES
            ('BAK', 'Бактериологическая', 'Бактериологическая лаборатория'),
            ('TH', 'Химическая', 'Химическая лаборатория'),
            ('TB', 'Токсико-биологическая', 'Токсико-биологическая лаборатория'),
            ('RV', 'Радиационная', 'Радиационная лаборатория'),
            ('PCR', 'ПЦР', 'Лаборатория ПЦР-диагностики')
        ON CONFLICT (code) DO NOTHING;
        """)

    # 2. Representative research goals per laboratory (research_goals.lab_id).
    op.execute("""
        INSERT INTO research_goals (code, name, comment, lab_id)
        SELECT src.goal_code, src.goal_name, 'Seeded lab reference goal', l.id
        FROM (
            VALUES
                ('BAK', 'RG-BAK-01', 'Общее микробное число (КМАФАнМ)'),
                ('BAK', 'RG-BAK-02', 'БГКП (колиформы)'),
                ('BAK', 'RG-BAK-03', 'Патогенные, в т.ч. сальмонеллы'),
                ('TH', 'RG-TH-01', 'Массовая доля влаги'),
                ('TH', 'RG-TH-02', 'Содержание нитратов'),
                ('TH', 'RG-TH-03', 'Кислотность'),
                ('TB', 'RG-TB-01', 'Токсичные элементы (свинец, кадмий)'),
                ('TB', 'RG-TB-02', 'Микотоксины'),
                ('TB', 'RG-TB-03', 'Пестициды'),
                ('RV', 'RG-RV-01', 'Удельная активность цезия-137'),
                ('RV', 'RG-RV-02', 'Удельная активность стронция-90'),
                ('RV', 'RG-RV-03', 'Суммарная бета-активность'),
                ('PCR', 'RG-PCR-01', 'ДНК ГМО'),
                ('PCR', 'RG-PCR-02', 'Видовая идентификация'),
                ('PCR', 'RG-PCR-03', 'Патогены методом ПЦР')
        ) AS src(lab_code, goal_code, goal_name)
        JOIN labs l ON l.code = src.lab_code
        ON CONFLICT (code) DO NOTHING;
        """)

    # 3. Indicators: each seeded goal × the first 5 reference sample types, so
    #    the (sample type + lab) → goals derivation is non-empty for them.
    op.execute(f"""
        INSERT INTO indicators (
            name, unit, norm_text, comment, research_goal_id, sample_type_id
        )
        SELECT
            rg.code || ' / ' || st.code,
            'ед.',
            'в пределах нормы',
            'Seeded lab reference indicator',
            rg.id,
            st.id
        FROM research_goals rg
        CROSS JOIN sample_types st
        WHERE rg.code ~ '{_GOAL_CODE_REGEX}'
          AND st.code IN (
              'SAMPLE-TYPE-001', 'SAMPLE-TYPE-002', 'SAMPLE-TYPE-003',
              'SAMPLE-TYPE-004', 'SAMPLE-TYPE-005'
          )
          AND NOT EXISTS (
              SELECT 1 FROM indicators i
              WHERE i.name = rg.code || ' / ' || st.code
          );
        """)


def downgrade() -> None:
    op.execute(f"""
        DELETE FROM indicators
        WHERE research_goal_id IN (
            SELECT id FROM research_goals WHERE code ~ '{_GOAL_CODE_REGEX}'
        );
        """)
    op.execute(f"DELETE FROM research_goals WHERE code ~ '{_GOAL_CODE_REGEX}';")
    op.execute("DELETE FROM labs WHERE code IN ('BAK', 'TH', 'TB', 'RV', 'PCR');")
