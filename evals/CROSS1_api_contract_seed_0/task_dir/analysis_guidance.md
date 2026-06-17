# Analysis Guidance — CROSS1_api_contract

## Tools to run
- `cat service/handlers.go` — read Go handler responses (source of truth)
- `cat service/models.go` — read Go JSON struct tags
- `cat client/api.py` — find what Python client expects
- `cat client/models.py` — find Python model field names
- `cat api_spec.yaml` — compare with actual server behavior

## The 3 Contract Mismatches

### Mismatch 1: User field name (camelCase vs snake_case)
**Go server** (models.go): `json:"userId"` tag → sends `{"userId": 123}`
**Python client** (models.py): `data.get("user_id")` → looks for `user_id` (WRONG)
**Spec**: says `user_id` (WRONG)
**Fix**: Update client to use `data.get("userId")` or add field aliasing

### Mismatch 2: Pagination response format
**Go server** (handlers.go): returns `{"data": [...], "next": "cursor_token"}`
**Python client** (api.py): parses `response["results"]` and `response["cursor"]` (WRONG)
**Spec**: says `{"results": [...], "cursor": "..."}` (WRONG)
**Fix**: Update client to parse `response["data"]` and `response["next"]`

### Mismatch 3: Error response format
**Go server** (handlers.go): returns HTTP 422 with `{"errors": ["message1", "message2"]}`
**Python client** (exceptions.py): expects HTTP 400 with `{"error": "single message"}` (WRONG)
**Spec**: says 400 with `{"error": "..."}` (WRONG)
**Fix**: Update client exception handling to expect 422 + `{"errors": [...]}`

## Tell Executor
1. Fix `client/models.py`: rename `user_id` → `userId` (or add from_dict with remapping)
2. Fix `client/api.py`: update pagination parsing to use `data`/`next` keys
3. Fix `client/exceptions.py`: update error parsing to expect 422 + `errors` array
4. Update `api_spec.yaml` to document the correct (server-actual) contract
5. Do NOT touch any `.go` files
