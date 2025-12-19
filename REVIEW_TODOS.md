# Design Review - Todo List

## 🔴 Critical (Security)

| # | Item | Severity | Priority | Status | Notes |
|---|------|----------|----------|--------|-------|
| 1 | JWT-based authentication | 🔴 Critical | P0 | ✅ DONE | Implemented cryptographically signed JWTs with 24h expiration |
| 2 | Restrict CORS origins | 🔴 Critical | P0 | ⏳ TODO | Change `Access-Control-Allow-Origin: '*'` to specific domains in production |
| 3 | Add `encrypted` column to messages table | 🔴 Critical | P0 | ✅ DONE | Added `encrypted INTEGER DEFAULT 0` to messages table schema |

---

## 🟠 High Priority (Architecture)

| # | Item | Severity | Priority | Status | Notes |
|---|------|----------|----------|--------|-------|
| 4 | Shard Durable Objects for scalability | 🟠 High | P1 | ⏳ TODO | Current single DO instance bottleneck for >1000 concurrent users |
| 5 | Add session expiration for E2EE | 🟠 High | P1 | ⏳ TODO | No mechanism to rotate/expire encryption sessions |
| 6 | Implement rate limiting on API endpoints | 🟠 High | P1 | ⏳ TODO | Missing protection against brute force and DoS attacks |

---

## 🟡 Medium Priority (Performance)

| # | Item | Severity | Priority | Status | Notes |
|---|------|----------|----------|--------|-------|
| 7 | Virtualize message lists | 🟡 Medium | P2 | ⏳ TODO | Full state update on each message causes re-renders for large conversations |
| 8 | Exponential backoff for WebSocket reconnection | 🟡 Medium | P2 | ⏳ TODO | Currently fixed 3-second reconnect interval - should implement jitter |
| 9 | Parallelize group message broadcasts | 🟡 Medium | P2 | ⏳ TODO | Sequential sends to group members - use `Promise.all` for parallel delivery |

---

## 🔵 Low Priority (Code Quality)

| # | Item | Severity | Priority | Status | Notes |
|---|------|----------|----------|--------|-------|
| 10 | Replace `any` types with proper interfaces | 🔵 Low | P3 | ⏳ TODO | Multiple locations with `(m: any)` - improve type safety |
| 11 | Add comprehensive error boundaries | 🔵 Low | P3 | ⏳ TODO | Missing error boundaries in React components |
| 12 | Implement logging/observability | 🔵 Low | P3 | ⏳ TODO | Add structured logging and monitoring for production |

---

## Summary Statistics

| Category | Count | Done | Todo |
|----------|-------|------|------|
| 🔴 Critical | 3 | 2 | 1 |
| 🟠 High | 3 | 0 | 3 |
| 🟡 Medium | 3 | 0 | 3 |
| 🔵 Low | 3 | 0 | 3 |
| **TOTAL** | **12** | **2** | **10** |

---

## Issues by System

### Security Issues (5 items)
- ✅ JWT Authentication (DONE)
- ✅ Database Schema (DONE)
- 🔴 CORS Configuration
- 🟠 Rate Limiting
- 🟠 Session Expiration

### Architecture Issues (3 items)
- 🟠 Durable Object Sharding
- 🟠 Session Expiration
- 🟠 Rate Limiting

### Performance Issues (3 items)
- 🟡 Message List Virtualization
- 🟡 WebSocket Reconnection
- 🟡 Group Broadcasting

### Code Quality Issues (3 items)
- 🔵 TypeScript Types
- 🔵 Error Boundaries
- 🔵 Logging

---

## Estimated Effort

| Priority | Items | Est. Time | Risk |
|----------|-------|-----------|------|
| P0 (Critical) | 1 item | 2 hours | High |
| P1 (High) | 3 items | 12-16 hours | High |
| P2 (Medium) | 3 items | 8-10 hours | Medium |
| P3 (Low) | 3 items | 6-8 hours | Low |
| **TOTAL** | **10 items** | **28-36 hours** | - |

---

## Recommended Implementation Order

1. **Phase 1 (Security First)** - Complete within 1 week
   - CORS restriction (2 hours)
   - Database schema update (1 hour)
   - Rate limiting (3 hours)

2. **Phase 2 (Stability)** - Complete within 2 weeks
   - Shard Durable Objects (6 hours)
   - E2EE session expiration (4 hours)
   - WebSocket reconnection backoff (3 hours)

3. **Phase 3 (Performance)** - Complete within 3 weeks
   - Message list virtualization (4 hours)
   - Group broadcast parallelization (3 hours)
   - Type safety improvements (4 hours)

4. **Phase 4 (Polish)** - Complete within 4 weeks
   - Error boundaries (2 hours)
   - Logging/observability (4 hours)
