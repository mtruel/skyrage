# Skyrage Code Review Backlog

**Review Date:** October 12, 2025  
**Status:** 31 tests passing, all lint/format/type checks green, no warnings

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
- [x] **Consolidate score doubling logic**: Currently implemented in both `model.Round.final_scores()` and `main.game_page()`. Extract to shared service/utility
- [x] **Consolidate player creation logic**: Duplicated across `api.create_player`, `main.create_player`, `api.create_game`, and `main.create_new_game`. Create single function
- [ ] **Improve deletion performance**: Replace O(N) full-table scan in `api.delete_player` with filtered SQL queries (JSON contains checks or normalized schema)
- [ ] **Fix N+1 queries in domain models**: `model.from_db()` methods open sessions and query per username. Refactor to accept session parameter or use eager loading
- [ ] **Standardize error messages**: Player deletion has inconsistent error messages ("part of game", "participated in games", "ended round"). Unify wording

### Testing - Core Functionality
- [ ] **Add API endpoint tests**: Test all REST endpoints in `api.py` (players CRUD, games CRUD, rounds create/list)
- [ ] **Add web handler tests**: Test form submissions and HTMX endpoints in `main.py`
- [ ] **Add domain model conversion tests**: Test `Round.from_db()` and `Game.from_db()` with various scenarios
- [ ] **Add config tests**: Test `get_database_url()` with missing file, in-memory DB, etc.
- [ ] **Add edge case tests**: Ties for game winner, boundary scores, finished game mutation attempts

---

## Larger Refactors (4-8 hours each)

### Architecture Decisions Needed
- [ ] **Domain model usage** ⚠️ **NEEDS INPUT**: Domain models (`Player`, `Round`, `Game`) exist but are unused by the app runtime (only in tests). Options:
  - A) Adopt domain layer throughout app (use in handlers, templates)
  - B) Remove domain layer entirely, keep DB-only approach
  - C) Keep for future refactor but acknowledge tech debt
  
- [ ] **Username editing behavior** ⚠️ **NEEDS INPUT**: `update_player_name` in game only mutates game's username list, not PlayerDB primary key. This creates divergence. Options:
  - A) Disallow username editing in games (only allow surname editing)
  - B) Properly rename PlayerDB record (requires migration of all references)
  - C) Document current behavior as intentional (game-local aliases)

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
