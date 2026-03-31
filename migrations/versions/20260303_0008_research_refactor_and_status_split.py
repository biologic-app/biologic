"""merge sample_targets+results into research and split status dictionaries

Revision ID: 20260303_0008
Revises: 20260303_0007
Create Date: 2026-03-03 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260303_0008"
down_revision = "20260303_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS direction_statuses (
            id uuid PRIMARY KEY DEFAULT uuidv7(),
            code text,
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at timestamptz
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS direction_statuses_direction_statuses_code
            ON direction_statuses (code)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS direction_statuses_direction_statuses_deleted_at
            ON direction_statuses (deleted_at)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sample_statuses (
            id uuid PRIMARY KEY DEFAULT uuidv7(),
            code text,
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at timestamptz
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS sample_statuses_sample_statuses_code
            ON sample_statuses (code)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS sample_statuses_sample_statuses_deleted_at
            ON sample_statuses (deleted_at)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS research_statuses (
            id uuid PRIMARY KEY DEFAULT uuidv7(),
            code text,
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at timestamptz
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS research_statuses_research_statuses_code
            ON research_statuses (code)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS research_statuses_research_statuses_deleted_at
            ON research_statuses (deleted_at)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS test_statuses (
            id uuid PRIMARY KEY DEFAULT uuidv7(),
            code text,
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at timestamptz
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS test_statuses_test_statuses_code
            ON test_statuses (code)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS test_statuses_test_statuses_deleted_at
            ON test_statuses (deleted_at)
        """
    )

    op.execute(
        """
        INSERT INTO direction_statuses (code, name)
        VALUES
            ('draft', 'Черновик'),
            ('registered', 'Зарегистрировано'),
            ('in_progress', 'В работе'),
            ('partially_completed', 'Частично выполнено'),
            ('completed', 'Выполнено')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO sample_statuses (code, name)
        VALUES
            ('pending', 'На регистрации'),
            ('registered', 'Зарегистрирован'),
            ('rejected', 'Брак'),
            ('in_progress', 'На исследовании'),
            ('analyzed', 'Обработан'),
            ('completed', 'Закрыт')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO research_statuses (code, name)
        VALUES
            ('draft', 'Черновик'),
            ('ordered', 'Запланировано'),
            ('in_progress', 'В работе'),
            ('completed', 'Завершено'),
            ('rejected', 'Отклонено')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO test_statuses (code, name)
        VALUES
            ('queued', 'Запланировано'),
            ('in_progress', 'Выполняется'),
            ('completed', 'Выполнено'),
            ('rejected', 'Отклонено')
        ON CONFLICT (code) DO NOTHING
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS research (
            id uuid PRIMARY KEY DEFAULT uuidv7(),
            sample_id uuid NOT NULL REFERENCES samples(id),
            research_goal_id uuid NOT NULL REFERENCES research_goals(id),
            status_id uuid REFERENCES research_statuses(id),
            comment text,
            recommendation text,
            received_at timestamptz,
            completed_at timestamptz,
            created_by uuid REFERENCES users(id),
            updated_by uuid REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at timestamptz
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS research_research_sample_id ON research (sample_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS research_research_research_goal_id ON research (research_goal_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS research_research_status_id ON research (status_id)")
    op.execute("CREATE INDEX IF NOT EXISTS research_research_received_at ON research (received_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS research_research_completed_at ON research (completed_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS research_research_deleted_at ON research (deleted_at)")

    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('public.results') IS NOT NULL THEN
            WITH fallback_goal AS (
              SELECT id FROM research_goals ORDER BY code NULLS LAST, id LIMIT 1
            ),
            st_pick AS (
              SELECT DISTINCT ON (st.sample_id)
                st.sample_id,
                st.research_goal_id,
                st.created_at
              FROM sample_targets st
              WHERE st.deleted_at IS NULL
              ORDER BY st.sample_id, st.created_at NULLS LAST, st.id
            )
            INSERT INTO research (
              id,
              sample_id,
              research_goal_id,
              status_id,
              comment,
              recommendation,
              received_at,
              completed_at,
              created_by,
              updated_by,
              created_at,
              updated_at,
              deleted_at
            )
            SELECT
              r.id,
              r.sample_id,
              COALESCE(sp.research_goal_id, fg.id),
              (SELECT id FROM research_statuses WHERE code = 'ordered' LIMIT 1),
              r.comment,
              r.recommendation,
              r.received_at,
              r.completed_at,
              r.created_by,
              r.updated_by,
              r.created_at,
              r.updated_at,
              r.deleted_at
            FROM results r
            LEFT JOIN st_pick sp ON sp.sample_id = r.sample_id
            CROSS JOIN fallback_goal fg
            WHERE COALESCE(sp.research_goal_id, fg.id) IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM research nr WHERE nr.id = r.id);
          ELSIF to_regclass('public.sample_targets') IS NOT NULL THEN
            INSERT INTO research (
              id,
              sample_id,
              research_goal_id,
              status_id,
              created_by,
              updated_by,
              created_at,
              updated_at,
              deleted_at
            )
            SELECT
              uuidv7(),
              st.sample_id,
              st.research_goal_id,
              (SELECT id FROM research_statuses WHERE code = 'draft' LIMIT 1),
              st.created_by,
              st.updated_by,
              st.created_at,
              st.updated_at,
              st.deleted_at
            FROM sample_targets st
            WHERE NOT EXISTS (
              SELECT 1
              FROM research r
              WHERE r.sample_id = st.sample_id
                AND r.research_goal_id = st.research_goal_id
                AND r.deleted_at IS NOT DISTINCT FROM st.deleted_at
            );
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('public.tests') IS NOT NULL THEN
            IF EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'tests'
                AND column_name = 'result_id'
            ) THEN
              ALTER TABLE tests RENAME COLUMN result_id TO research_id;
            END IF;

            ALTER TABLE tests DROP CONSTRAINT IF EXISTS fk_tests_result_id_results_id;
            ALTER TABLE tests DROP CONSTRAINT IF EXISTS tests_result_id_fkey;
            ALTER TABLE tests DROP CONSTRAINT IF EXISTS fk_tests_status_id_statuses_id;
            ALTER TABLE tests DROP CONSTRAINT IF EXISTS fk_tests_status_id_test_statuses_id;

            ALTER TABLE tests
              ADD CONSTRAINT fk_tests_research_id_research_id
              FOREIGN KEY (research_id) REFERENCES research(id);

            UPDATE tests
            SET status_id = (SELECT id FROM test_statuses WHERE code = 'queued' LIMIT 1)
            WHERE status_id IS NOT NULL;

            ALTER TABLE tests
              ADD CONSTRAINT fk_tests_status_id_test_statuses_id
              FOREIGN KEY (status_id) REFERENCES test_statuses(id);
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('public.directions') IS NOT NULL THEN
            UPDATE directions
            SET status_id = (SELECT id FROM direction_statuses WHERE code = 'registered' LIMIT 1)
            WHERE status_id IS NOT NULL;

            ALTER TABLE directions DROP CONSTRAINT IF EXISTS fk_directions_status_id_statuses_id;
            ALTER TABLE directions DROP CONSTRAINT IF EXISTS fk_directions_status_id_direction_statuses_id;
            ALTER TABLE directions
              ADD CONSTRAINT fk_directions_status_id_direction_statuses_id
              FOREIGN KEY (status_id) REFERENCES direction_statuses(id);
          END IF;

          IF to_regclass('public.samples') IS NOT NULL THEN
            UPDATE samples
            SET status_id = (SELECT id FROM sample_statuses WHERE code = 'pending' LIMIT 1)
            WHERE status_id IS NOT NULL;

            ALTER TABLE samples DROP CONSTRAINT IF EXISTS fk_samples_status_id_statuses_id;
            ALTER TABLE samples DROP CONSTRAINT IF EXISTS fk_samples_status_id_sample_statuses_id;
            ALTER TABLE samples
              ADD CONSTRAINT fk_samples_status_id_sample_statuses_id
              FOREIGN KEY (status_id) REFERENCES sample_statuses(id);
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('public.indicators') IS NOT NULL THEN
            IF NOT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'indicators'
                AND column_name = 'research_goal_id'
            ) THEN
              ALTER TABLE indicators ADD COLUMN research_goal_id uuid;
            END IF;

            IF EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'indicators'
                AND column_name = 'lab_id'
            ) THEN
              UPDATE indicators i
              SET research_goal_id = COALESCE(
                i.research_goal_id,
                (
                  SELECT rg.id
                  FROM research_goals rg
                  WHERE rg.lab_id = i.lab_id
                  ORDER BY rg.code NULLS LAST, rg.id
                  LIMIT 1
                )
              );

              ALTER TABLE indicators DROP CONSTRAINT IF EXISTS fk_indicators_lab_id_labs_id;
              DROP INDEX IF EXISTS indicators_indicators_lab_id;
              ALTER TABLE indicators DROP COLUMN lab_id;
            END IF;

            ALTER TABLE indicators DROP CONSTRAINT IF EXISTS fk_indicators_research_goal_id_research_goals_id;
            ALTER TABLE indicators
              ADD CONSTRAINT fk_indicators_research_goal_id_research_goals_id
              FOREIGN KEY (research_goal_id) REFERENCES research_goals(id);

            CREATE INDEX IF NOT EXISTS indicators_indicators_research_goal_id
              ON indicators (research_goal_id);
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('public.conclusions') IS NOT NULL THEN
            IF NOT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'conclusions'
                AND column_name = 'code'
            ) THEN
              ALTER TABLE conclusions ADD COLUMN code text;
            END IF;
            IF NOT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'conclusions'
                AND column_name = 'name'
            ) THEN
              ALTER TABLE conclusions ADD COLUMN name text;
            END IF;
            IF NOT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'conclusions'
                AND column_name = 'text_singular'
            ) THEN
              ALTER TABLE conclusions ADD COLUMN text_singular text;
            END IF;
            IF NOT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'conclusions'
                AND column_name = 'text_plural'
            ) THEN
              ALTER TABLE conclusions ADD COLUMN text_plural text;
            END IF;

            IF EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = 'public'
                AND table_name = 'conclusions'
                AND column_name = 'conclusion_status_id'
            ) THEN
              IF to_regclass('public.conclusion_statuses') IS NOT NULL THEN
                UPDATE conclusions c
                SET
                  code = COALESCE(c.code, cs.code),
                  name = COALESCE(c.name, cs.name),
                  text_singular = COALESCE(c.text_singular, cs.name),
                  text_plural = COALESCE(c.text_plural, cs.name)
                FROM conclusion_statuses cs
                WHERE c.conclusion_status_id = cs.id;
              END IF;

              ALTER TABLE conclusions DROP CONSTRAINT IF EXISTS fk_conclusions_conclusion_status_id_conclusion_statuses_id;
              ALTER TABLE conclusions DROP COLUMN conclusion_status_id;
            END IF;

            UPDATE conclusions
            SET
              code = COALESCE(code, 'CONCLUSION-' || LEFT(id::text, 8)),
              name = COALESCE(name, 'Заключение'),
              text_singular = COALESCE(text_singular, 'Заключение'),
              text_plural = COALESCE(text_plural, 'Заключения');

            ALTER TABLE conclusions ALTER COLUMN code SET NOT NULL;
            ALTER TABLE conclusions ALTER COLUMN name SET NOT NULL;
            ALTER TABLE conclusions ALTER COLUMN text_singular SET NOT NULL;
            ALTER TABLE conclusions ALTER COLUMN text_plural SET NOT NULL;

            CREATE UNIQUE INDEX IF NOT EXISTS conclusions_conclusions_code
              ON conclusions (code);
            DROP INDEX IF EXISTS conclusions_conclusions_status_id;
          END IF;

          DROP TABLE IF EXISTS conclusion_statuses;
        END $$;
        """
    )

    op.execute("DROP TABLE IF EXISTS sample_targets")
    op.execute("DROP TABLE IF EXISTS results")
    op.execute("DROP TABLE IF EXISTS statuses")


def downgrade() -> None:
    pass
