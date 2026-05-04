---
name: tet-atf-knowledge:04-utils-catalog
description: Reference catalog of all TET-ATF utility modules in src/util/ — Logger, TestContext, DataGenerator, DateUtils, ConfigUtils, ConverterUtils, ValidatorUtils, StorageUtils, and UserManager — with their full method signatures. Use when implementing any code that needs logging, test data, dates, config access, type conversion, schema validation, file I/O, or test-account provisioning.
---

# Skill 04 — Utils Catalog

All utility modules live in `src/util/`. Use these functions; do not re-implement them.

---

## Logger

```
trace(message, context?)  → void
debug(message, context?)  → void
info(message, context?)   → void
warn(message, context?)   → void
error(message, error?, context?) → void
setLevel(level)           → void
```
**Context dict always includes**: `testId`, `tags`, `executionId`, `timestamp`  
**Sensitive fields always masked** — see Skill 11.

---

## TestContext

```
initialize(testId, tags?)           → void
set(key, value)                     → void
get(key)                            → Any
getAs(key)                          → typed value
has(key)                            → Boolean
trackResource(type, id, identifier?) → void
getResourcesForCleanup()            → Array[Resource]
clear()                             → void
getTestMetadata()                   → Dict
```

---

## DataGenerator

```
generateUniqueId(prefix?)    → String     # e.g. "USER-abc123"
generateEmail()              → String
generateUsername()           → String
generateFirstName()          → String
generateLastName()           → String
generatePhoneNumber()        → String
generateAddress()            → String
generatePostalCode()         → String
generateCity()               → String
generateCountry()            → String
generateRandomString(length?) → String
generateRandomNumber(min?, max?) → Number
generateFutureDate(years?)   → Date
generatePastDate(years?)     → Date
```

---

## DateUtils

```
now() / utcNow() / today() / tomorrow() / yesterday()
nextMonday/Tuesday/.../Sunday(fold?)  → date
lastMonday/Tuesday/.../Sunday(fold?)  → date
addDays(date, days)     → Date
addHours(date, hours)   → Date
addMinutes(date, min)   → Date
addMonths(date, months) → Date
formatISO(date)         → String
formatDate(date, fmt?)  → String
formatTime(date)        → String
parseISO(isoString)     → Date
isPast(date) / isFuture(date) → Boolean
diffInDays(d1, d2)      → Integer
diffInHours(d1, d2)     → Integer
```

---

## ConfigUtils

```
initialize(configDir?)  → void
get(key, default?)      → Any       # e.g. "api.auth_service.base_url"
set(key, value)         → void
getEnv()                → String    # current environment name
getAll()                → Dict
```

---

## ConverterUtils

Type conversion and data transformation from test inputs to target types.

```
to_int(value) → int
to_float(value) → float
to_bool(value) → bool
to_date(value, fmt?) → date
to_datetime(value, fmt?) → datetime
to_enum(value, enum_class) → Enum
dict_to_object(data, cls) → object
snake_to_camel(text) → str
camel_to_snake(text) → str
```

---

## ValidatorUtils

Generic schema and value validation. Used primarily by `BaseApiClient` (transparently) and in unit tests.

```
validate_schema(data, schema_path)        → void   # raises on JSON Schema violation
validate_json_schema(data, schema)        → bool
validate_not_empty(value, field_name?)    → void   # raises ValueError if falsy
validate_type(value, expected_type)       → bool
validate_range(value, min_val, max_val)   → bool
validate_regex(value, pattern)            → bool
```

---

## StorageUtils

Generic file I/O and archive helpers for test artifacts. Used by the reporting pipeline.

```
save_json(data, path)              → Path
load_json(path)                    → dict
save_text(content, path)           → Path
load_text(path)                    → str
ensure_dir(path)                   → Path
delete_file(path)                  → void
list_files(directory, pattern?)    → List[Path]
zip_directory(source_dir, output_path) → Path
```

---

## UserManager

Singleton that provides pre-existing test accounts. Use this whenever a test needs
a real login/password/token (e.g. to call a login API or fill a login form). Do NOT use
DataGenerator for credentials — generated users don't exist in the system under test.

Credentials are read directly from the `USER_CATALOG` environment variable — a YAML
string mapping role names to a dict of fields. No config file or source dispatch
is needed.

```
# Singleton
UserManager.get_instance()   → UserManager
UserManager.reset()          → None                 # test teardown helper

# Lookup
get_user(role?)              → User                 # raises ValueError if role is missing or catalog is invalid

# Frozen dataclass — all fields accessed via get(); login and password are convenience properties
User.login           → str | None    # shortcut for user.get("login")
User.password        → str | None    # shortcut for user.get("password")
User.get(key, default?) → Any        # access any catalog field by name
```

**Required env var** — `USER_CATALOG` must be set to a YAML mapping of role → credential
fields. No field is mandatory — the only constraint is that an entry is non-empty:
```yaml
# Classic login + password
default:
  login: user@example.com
  password: secret

# Login + password + extra factors
admin:
  login: admin@example.com
  password: hunter2
  token: my-api-token
  mfa_secret: TOTP_BASE32_SECRET

# Token-only service account (no login or password)
service_account:
  token: bearer-token

# Certificate-only account
cert_user:
  certificate: CERT_PEM_CONTENT
  key: PRIVATE_KEY_CONTENT
```
If `USER_CATALOG` is not set or empty, `UserManager` raises at startup with a clear error.
For Kubernetes, the catalog is injected via Helm `secretKeyRef` — see Skill 13.
For local development, set it in `.env`.

See Skill 13 for full K8s Secret layout and Helm wiring details.
See Skill 11 for credential security rules.

---

## Test Coverage References

→ [references/REFERENCE.md](references/REFERENCE.md) — linked stories (MAINT-001, REL-001, REL-002) and test cases (TC-MAINT-1-004, TC-REL-1-xxx, TC-REL-2-001)
