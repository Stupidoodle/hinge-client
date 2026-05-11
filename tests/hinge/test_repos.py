"""Unit tests for the four SQL repositories: profile, decision, session, prompts."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hinge.domain.models.decision import HingeDecision
from hinge.domain.models.profile import HingeProfile
from hinge.domain.models.prompt import HingePrompt
from hinge.domain.models.swipe_session import HingeSwipeSession
from hinge.infrastructure.db.mappers import start_hinge_mappers
from hinge.infrastructure.db.metadata import metadata
from hinge.infrastructure.db.unit_of_work import HingeSqlAlchemyUnitOfWork


@pytest.fixture
def uow_factory():
    """Yield a sessionmaker backed by an in-memory SQLite with mappers installed."""
    start_hinge_mappers()
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# HingeProfileRepo
# ---------------------------------------------------------------------------


def test_profile_add_and_get(uow_factory):
    """add() persists, get() round-trips by subject_id."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.add(
            HingeProfile(subject_id="s1", first_name="Alice", age=27),
        )
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        p = uow.profiles.get("s1")
        assert p is not None
        assert p.first_name == "Alice"
        assert p.age == 27
        assert uow.profiles.get("missing") is None


def test_profile_list_and_count(uow_factory):
    """list_all paginates; count totals."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        for i in range(5):
            uow.profiles.add(HingeProfile(subject_id=f"s{i}", first_name=f"P{i}"))
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.profiles.count() == 5
        page = uow.profiles.list_all(limit=3)
        assert len(page) == 3


def test_profile_search_by_name_and_age(uow_factory):
    """search() filters by name substring (case-insensitive) + age window."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.add(HingeProfile(subject_id="a", first_name="Anna", age=25))
        uow.profiles.add(HingeProfile(subject_id="b", first_name="Joanna", age=30))
        uow.profiles.add(HingeProfile(subject_id="c", first_name="Bob", age=28))
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        # Both "Anna" and "Joanna" contain the substring "ann".
        anns = uow.profiles.search(name="ann")
        assert {p.subject_id for p in anns} == {"a", "b"}
        adults = uow.profiles.search(min_age=27, max_age=29)
        assert {p.subject_id for p in adults} == {"c"}


def test_profile_rejection_flow_mark_count_clear(uow_factory):
    """mark_likely_rejected → count_by_rejection_type → clear_false_rejections."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.add(HingeProfile(subject_id="x", first_name="X"))
        uow.profiles.add(HingeProfile(subject_id="y", first_name="Y"))
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        n = uow.profiles.mark_likely_rejected({"x", "y"})
        uow.commit()
        assert n == 2

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.set_rejection_type("x", "passed")
        uow.profiles.set_rejection_type("y", "gone")
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.profiles.count_by_rejection_type("passed") == 1
        assert uow.profiles.count_by_rejection_type("gone") == 1
        # x reappears in a fresh scan — should be un-flagged
        cleared = uow.profiles.clear_false_rejections({"x"})
        uow.commit()
        assert cleared == 1

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        x = uow.profiles.get("x")
        assert x is not None
        assert x.likely_rejected is False


def test_profile_miss_count_increment_reset(uow_factory):
    """increment_miss_count + reset_miss_count work pairwise."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.add(HingeProfile(subject_id="m", first_name="M"))
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.increment_miss_count({"m"})
        uow.profiles.increment_miss_count({"m"})
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.profiles.get("m").miss_count == 2
        uow.profiles.reset_miss_count({"m"})
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.profiles.get("m").miss_count == 0


def test_profile_get_undecided_excludes_decided_and_rejected(uow_factory):
    """get_undecided_subject_ids excludes decided + likely_rejected profiles."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.add(HingeProfile(subject_id="u1", first_name="U1"))
        uow.profiles.add(HingeProfile(subject_id="u2", first_name="U2"))
        uow.profiles.add(HingeProfile(subject_id="u3", first_name="U3"))
        uow.decisions.add(
            HingeDecision(
                profile_subject_id="u1",
                action="like",
                decided_at=datetime.now(UTC),
            ),
        )
        uow.profiles.mark_likely_rejected({"u2"})
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        ids = uow.profiles.get_undecided_subject_ids()
        assert ids == {"u3"}


def test_profile_untyped_rejections(uow_factory):
    """get_untyped_rejections returns rejections with rejection_type=NULL."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.add(HingeProfile(subject_id="a", first_name="A"))
        uow.profiles.add(HingeProfile(subject_id="b", first_name="B"))
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.mark_likely_rejected({"a", "b"})
        uow.profiles.set_rejection_type("a", "passed")
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.profiles.get_untyped_rejections() == {"b"}


# ---------------------------------------------------------------------------
# HingeDecisionRepo
# ---------------------------------------------------------------------------


def test_decision_add_and_query(uow_factory):
    """add(), get_by_subject(), decided_subject_ids() — basic decision flow."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.profiles.add(HingeProfile(subject_id="d1", first_name="D1"))
        uow.profiles.add(HingeProfile(subject_id="d2", first_name="D2"))
        now = datetime.now(UTC)
        uow.decisions.add(
            HingeDecision(
                profile_subject_id="d1",
                action="like",
                decided_at=now,
                score=82.5,
                reasoning="vibes",
            ),
        )
        uow.decisions.add(
            HingeDecision(
                profile_subject_id="d2",
                action="skip",
                decided_at=now,
            ),
        )
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        d1 = uow.decisions.get_by_subject("d1")
        assert d1 is not None
        assert d1.action == "like"
        assert d1.score == 82.5
        assert uow.decisions.get_by_subject("never") is None
        decided = uow.decisions.decided_subject_ids(["d1", "d2", "never"])
        assert decided == {"d1", "d2"}
        assert uow.decisions.count_by_action("like") == 1
        assert uow.decisions.count_by_action("skip") == 1
        assert uow.decisions.count() == 2


def test_decision_avg_score_and_daily_stats(uow_factory):
    """avg_score over likes; daily_stats groups by day."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        for i, sc in enumerate([60.0, 80.0, 100.0]):
            uow.profiles.add(HingeProfile(subject_id=f"a{i}", first_name=f"A{i}"))
            uow.decisions.add(
                HingeDecision(
                    profile_subject_id=f"a{i}",
                    action="like",
                    decided_at=datetime.now(UTC),
                    score=sc,
                ),
            )
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        avg = uow.decisions.avg_score()
        assert avg is not None
        assert 79.0 < avg < 81.0  # mean = 80
        stats = uow.decisions.daily_stats(since_days=7)
        # At least one bucket should report 3 likes today.
        assert any(s.get("liked") == 3 for s in stats)


# ---------------------------------------------------------------------------
# HingeSessionRepo (swipe sessions)
# ---------------------------------------------------------------------------


def test_swipe_session_add_get_update(uow_factory):
    """SessionRepo persists swipe-session analytics, supports merge-style update."""
    started = datetime.now(UTC) - timedelta(minutes=10)
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        sess = HingeSwipeSession(started_at=started)
        uow.sessions.add(sess)
        uow.commit()
        assigned_id = sess.id

    assert assigned_id is not None

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        got = uow.sessions.get(assigned_id)
        assert got is not None
        assert got.profiles_seen == 0
        assert uow.sessions.count() == 1

        got.profiles_seen = 12
        got.likes_sent = 3
        uow.sessions.update(got)
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        got = uow.sessions.get(assigned_id)
        assert got is not None
        assert got.profiles_seen == 12
        assert got.likes_sent == 3


# ---------------------------------------------------------------------------
# HingePromptsRepo (catalog)
# ---------------------------------------------------------------------------


def test_prompts_bulk_upsert_and_lookup(uow_factory):
    """bulk_upsert is idempotent; get/get_text/list_all/count behave."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        n = uow.prompts.bulk_upsert(
            [
                HingePrompt(
                    prompt_id="p1",
                    text="Two truths and a lie",
                    categories=["fun"],
                ),
                HingePrompt(prompt_id="p2", text="Dorkiest thing"),
            ],
        )
        uow.commit()
        assert n == 2

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.prompts.count() == 2
        p1 = uow.prompts.get("p1")
        assert p1 is not None
        assert p1.text == "Two truths and a lie"
        assert uow.prompts.get_text("p2") == "Dorkiest thing"
        assert uow.prompts.get_text("nope") is None
        catalog = uow.prompts.list_all()
        assert {p.prompt_id for p in catalog} == {"p1", "p2"}

    # Upserting again with updated text should not duplicate rows.
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        uow.prompts.bulk_upsert([HingePrompt(prompt_id="p1", text="UPDATED")])
        uow.commit()

    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.prompts.count() == 2
        assert uow.prompts.get_text("p1") == "UPDATED"


def test_prompts_bulk_upsert_empty_is_noop(uow_factory):
    """Upserting an empty list returns 0 without DB churn."""
    with HingeSqlAlchemyUnitOfWork(uow_factory) as uow:
        assert uow.prompts.bulk_upsert([]) == 0
        assert uow.prompts.count() == 0
