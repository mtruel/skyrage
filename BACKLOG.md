# Skyrage Code Review Backlog

**Review Date:** October 12, 2025  
**Status:** 111 tests passing, all lint/format/type checks green, no warnings

---

## Quick Wins (Easy, <1 hour each)

### Fix Inconsistencies
- [x] **Score range validation mismatch**: Client validates -15..120, server validates -5..120. Need to align both (decision needed: which range is correct per Skyjo rules? -15 is the right one, based on the cards available three columns with -2 -2 -1)
- [x] **API create_player status code**: Returns 201 for existing players; should return 200 instead when player already exists
- [x] **Remove dead code**: Delete unused `update_score` endpoint stub in `main.py`
- [x] **Remove test dummy**: Delete `src/tests/test_dummy.py` (only contains `assert True`)
- [x] **Add explicit return types**: Add type hints to `db.get_engine()` and `db.get_session_maker()` 
- [x] **Fix SQLAlchemy warning**: Address SAWarning in `test_db.py::test_player_unique_username` (session identity conflict)

### Documentation
- [x] **Document score range**: Add comment in code and/or `SKYJO_RULES.md` clarifying valid score range
---

## Medium Effort (2-4 hours each)

### Code Quality & Maintainability
- [x] **Consolidate score doubling logic**: ✅ Resolved by adopting domain models. `main.game_page()` now uses `Round.final_scores()` from domain model instead of duplicating logic.
- [x] **Consolidate player creation logic**: Duplicated across `api.create_player`, `main.create_player`, `api.create_game`, and `main.create_new_game`. Create single function
- [ ] **Improve deletion performance**: Replace O(N) full-table scan in `api.delete_player` with filtered SQL queries (JSON contains checks or normalized schema)
- [x] **Fix N+1 queries in domain models**: `model.from_db()` methods open sessions and query per username. Refactor to accept session parameter or use eager loading
- [x] **Standardize error messages**: Player deletion has inconsistent error messages ("part of game", "participated in games", "ended round"). Unify wording

### Testing - Core Functionality
- [x] **Add API endpoint tests**: Test all REST endpoints in `api.py` (players CRUD, games CRUD, rounds create/list)
- [ ] **Add web handler tests**: Test form submissions and HTMX endpoints in `main.py`
- [x] **Add domain model conversion tests**: Test `Round.from_db()` and `Game.from_db()` with various scenarios
- [x] **Add config tests**: Test `get_database_url()` with missing file, in-memory DB, etc.
- [x] **Add edge case tests**: Ties for game winner, boundary scores, finished game mutation attempts

---

## Larger Refactors (4-8 hours each)

### Architecture Decisions Needed
- [x] **Domain model usage** ✅ **IMPLEMENTED**: Domain models (`Player`, `Round`, `Game`) are now used in production runtime.
  - **Decision:** Option A - Adopt domain layer throughout app
  - **Implementation:** `main.game_page()` now uses `Game.from_db()` and its methods (`player_total_scores()`, `winner()`, etc.)
  - **Benefits:** Eliminated score calculation duplication, centralized business logic in domain models, maintained existing template interface
  - **Status:** All 111 tests passing, linter/formatter/type checks green
  
- [x] **Username editing behavior** ✅ **RESOLVED - Option A implemented**: Usernames are now immutable after creation
  - **Problem:** `update_player_name` endpoint mutated game's username list but not PlayerDB primary key, creating divergence between game records and round data
  - **Solution:** Removed `update_player_name` endpoint from `main.py` (was not used in UI)
  - **Implementation:**
    - Created new `PlayerUpdate` model in `api.py` that only accepts surname changes
    - Updated `PUT /api/players/{username}` to use `PlayerUpdate` (rejects username changes)
    - Added comprehensive test suite in `test_username_immutability.py` (5 tests)
    - Usernames remain stable as primary keys; surnames can be edited for personalization
  - **Benefits:** Maintains data integrity, prevents orphaned records, aligns with database best practices
  - **Status:** All 116 tests passing, linter/formatter/type checks green

### Performance & Scalability
- [ ] **JSON schema normalization** ⚠️ **NEEDS INPUT**: Player usernames and scores stored as JSON limits query-ability. Options:
  - A) Keep current schema (simple, works for small data)
  - B) Add normalized tables (GamePlayers, RoundScores) for better queries
  - C) Add indexes on JSON fields (SQLite 3.38+)

### Template & Logic Separation
- [ ] **Extract template calculation logic**: `main.game_page()` duplicates score calculation logic. Move to domain model or service layer
- [ ] **Standardize HTMX responses**: Some endpoints return inline HTML strings, others use templates. Pick one approach

---

## Nice to Have (Future)

### Additional Testing
- [ ] **Integration tests**: End-to-end game flow (create → add rounds → end game)
- [ ] **HTMX interaction tests**: Test dynamic UI updates, modals, form submissions
- [ ] **Error path tests**: 404s, 400s, constraint violations at API level

### Code Organization
- [ ] **Create service layer**: Extract business logic from `api.py` and `main.py` into shared services
- [ ] **Type template contexts**: Use TypedDict for Jinja template context dictionaries
- [ ] **Explicit handler return types**: Add return type annotations to FastAPI handlers

### Security & Robustness
- [ ] **CSRF protection**: Add if deploying beyond local use
- [ ] **Authentication**: Add user/session management if needed
- [ ] **Input sanitization audit**: Review all form inputs for edge cases

### UI/UX Polish
- [ ] **Consolidate delete confirmation JS**: Shared logic between `index.html` and `players.html`
- [ ] **Consistent HTMX patterns**: Game deletion uses fetch+JSON, other deletes use different patterns
- [ ] **Explicit round ender UI**: Currently defaults to first player if none selected; make selection required or more obvious

---

## Blocked / Need Clarification ⚠️

These items require your decision before proceeding:

1. **Score range**: What's the official Skyjo range? -5 to 120 or -15 to 120?
2. **Domain model strategy**: Keep or remove the Pydantic domain models?
3. **Username editing**: Should games have local aliases or enforce global username consistency?
4. **Schema normalization**: Keep JSON or normalize to tables?
5. **Round ender default**: Require explicit selection or keep current fallback to first player?

---

## Priority Recommendation

### Sprint 1: Foundation fixes (1-2 days)
1. Quick wins section (all)
2. Consolidate score doubling logic
3. Add API endpoint tests

### Sprint 2: Architecture decisions (requires input)
1. Decide on domain model strategy
2. Decide on username editing behavior
3. Based on decisions, implement chosen approach

### Sprint 3: Performance & quality (2-3 days)
1. Fix deletion performance
2. Fix N+1 queries
3. Add edge case tests
4. Consolidate player creation logic

---

## Notes

- Current state: **All checks passing** ✅
- Technical debt: **Medium** (unused domain layer, logic duplication)
- Test coverage: **Partial** (good model tests, missing API/handler tests)
- Performance: **Adequate for small scale**, will need optimization for growth
