# UNIVERSAL SOFTWARE ENGINEERING PATTERNS CODEBASE

## ROLE

You are a principal software engineer and software architecture researcher.

Your task is to build a **Universal Software Engineering Patterns Reference Codebase**.

This is NOT a product application.

This is NOT a single-project boilerplate.

This is a reusable engineering reference implementation containing the **recurring patterns, abstractions, workflows, integrations, architectural decisions and implementation techniques that software engineers repeatedly need across different types of software products.**

The purpose is to create a codebase that I can study, copy from, adapt, and use as the foundation for future projects.

I work primarily with:

### Backend

* Python
* Django
* Django REST Framework
* FastAPI
* PostgreSQL
* Redis

### Mobile

* Flutter
* Dart
* Riverpod
* Firebase

### Web

* React
* TypeScript
* modern React architecture

The codebase should demonstrate the **same software engineering concepts across these ecosystems wherever the concept applies**.

---

# CORE PHILOSOPHY

Do NOT organize this project around a hypothetical product.

Instead organize it around:

> "What does a software engineer repeatedly have to solve when building real software?"

For example:

Authentication is not a product feature.

Routing is not a product feature.

Pagination is not a product feature.

Error handling is not a product feature.

Forms are not a product feature.

API clients are not a product feature.

State management is not a product feature.

File uploads are not a product feature.

Caching is not a product feature.

Notifications are not a product feature.

Authorization is not a product feature.

These are recurring engineering problems.

The reference repository should provide working implementations of these recurring problems.

---

# 1. BUILD A PATTERN CATALOGUE FIRST

Before writing substantial code, create a catalogue of recurring software engineering concerns.

Group them into categories.

At minimum:

```text
01-foundations
02-architecture
03-authentication
04-authorization
05-routing
06-state-management
07-networking
08-data-access
09-database
10-forms-validation
11-pagination
12-search-filtering
13-caching
14-file-storage
15-notifications
16-background-processing
17-real-time
18-payments
19-webhooks
20-security
21-observability
22-testing
23-performance
24-offline
25-local-storage
26-configuration
27-internationalization
28-accessibility
29-deep-linking
30-error-handling
31-logging
32-ci-cd
33-devops
34-documentation
35-scalability
```

Do not blindly assume this list is complete.

Research the architecture and add other recurring concerns that a senior software engineer would reasonably expect.

---

# 2. CROSS-STACK PRINCIPLE

For every recurring engineering concept, determine how it is implemented in each stack.

For example:

```text
Authentication

Flutter/Dart
    Firebase Auth
    Riverpod
    Auth Repository
    Auth State
    Google
    Email
    Phone/OTP

React/TypeScript
    Auth Provider
    Auth Context
    Protected Routes
    API authentication
    token handling

Django/Python
    Authentication
    Token verification
    User model
    Permissions
    Sessions
    RBAC
```

Do this systematically.

The goal is to understand:

> Same engineering problem → different implementation for each ecosystem.

---

# 3. FLUTTER / DART REFERENCE IMPLEMENTATION

Create a complete Flutter reference application demonstrating recurring mobile engineering patterns.

Use:

* Flutter
* Dart
* Riverpod
* Firebase
* clean architecture where useful

Do not build a fake application.

Build a **Patterns Demo Application** where each screen demonstrates a particular engineering concept.

---

# 4. FLUTTER PROJECT STRUCTURE

Create a structure similar to:

```text
flutter_reference/
│
├── lib/
│   │
│   ├── core/
│   │   ├── config/
│   │   ├── constants/
│   │   ├── errors/
│   │   ├── extensions/
│   │   ├── logging/
│   │   ├── networking/
│   │   ├── storage/
│   │   ├── utils/
│   │   └── validators/
│   │
│   ├── data/
│   │   ├── datasources/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── services/
│   │
│   ├── domain/
│   │   ├── entities/
│   │   ├── repositories/
│   │   └── usecases/
│   │
│   ├── features/
│   │   ├── auth/
│   │   ├── routing/
│   │   ├── home/
│   │   ├── forms/
│   │   ├── pagination/
│   │   ├── search/
│   │   ├── uploads/
│   │   ├── notifications/
│   │   ├── profile/
│   │   └── settings/
│   │
│   ├── routing/
│   ├── services/
│   ├── shared/
│   └── main.dart
│
├── test/
└── integration_test/
```

Adapt this where necessary.

---

# 5. FLUTTER AUTHENTICATION

Create a complete Firebase Authentication implementation.

Demonstrate:

## Email

```text
Register
Login
Logout
Email verification
Resend verification
Forgot password
Reset password
Change password
Account deletion
Session restoration
```

## Google

Implement:

```text
Google sign-in
Existing account handling
New account handling
Logout
Session restoration
Error handling
```

## Phone

Implement:

```text
Phone number entry
OTP
OTP verification
Resend OTP
OTP timeout
Invalid OTP
Verification state
Logout
```

Use Firebase Authentication.

---

# 6. FLUTTER AUTH ARCHITECTURE

Do not put Firebase calls directly into widgets.

Demonstrate:

```text
UI
 ↓
Riverpod Provider
 ↓
Auth Controller
 ↓
Auth Repository
 ↓
Firebase Auth Data Source
 ↓
Firebase
```

Demonstrate:

```text
AuthState
Authenticated
Unauthenticated
Loading
Error
EmailVerificationRequired
PhoneVerification
```

The architecture should be reusable in future projects.

---

# 7. FLUTTER RIVERPOD PATTERNS

Demonstrate multiple useful Riverpod patterns:

```text
Provider
FutureProvider
StreamProvider
StateProvider
StateNotifier / Notifier
AsyncNotifier
Family
AutoDispose
Provider dependencies
Provider overrides
Repository providers
Authentication providers
Pagination providers
```

Show when each pattern should be used.

Do not use every provider type merely for demonstration.

Each example should have a documented reason.

---

# 8. FLUTTER FIREBASE DATA ACCESS

Demonstrate Firebase data access patterns.

Include:

```text
Firestore
Firebase Storage
Firebase Auth
Firebase Cloud Messaging
Crashlytics
Analytics where appropriate
```

For Firestore demonstrate:

```text
Create
Read
Update
Delete
Streams
Queries
Filtering
Ordering
Pagination
Transactions
Batched writes
Document references
Subcollections
```

Show:

```text
Firestore
 ↓
Data Source
 ↓
Repository
 ↓
Domain
 ↓
Riverpod
 ↓
UI
```

Do not directly query Firestore from UI widgets.

---

# 9. FLUTTER ROUTING

Create a comprehensive routing reference.

Demonstrate:

```text
Public routes
Protected routes
Authentication guards
Nested routes
Route parameters
Query parameters
Deep links
Unknown routes
Redirects
Navigation state
Bottom navigation
Nested navigation
Modal routes
```

Include examples such as:

```text
/login
/register
/home
/profile
/users/:id
/posts/:id
/settings
```

Document how the routing system should be adapted to a real application.

---

# 10. FLUTTER NETWORKING

Create a reusable API client.

Demonstrate:

```text
GET
POST
PUT
PATCH
DELETE
multipart upload
download
timeouts
retry
authentication headers
token refresh
interceptors
request logging
error mapping
```

Use a proper networking abstraction.

Demonstrate:

```text
API Client
 ↓
Remote Data Source
 ↓
Repository
 ↓
Use Case
 ↓
Riverpod
 ↓
UI
```

---

# 11. FLUTTER STATE PATTERNS

Demonstrate state patterns for:

```text
Loading
Success
Error
Empty
Refreshing
Pagination
Optimistic updates
Form state
Authentication state
Connectivity state
```

Show both simple and complex state patterns.

---

# 12. FLUTTER FORMS

Create examples for:

```text
Login
Registration
Profile editing
Password change
Payment form
Multi-step form
Dynamic form
```

Demonstrate:

```text
Validation
Async validation
Field errors
Submission state
Server errors
Keyboard handling
Focus management
Form restoration
```

---

# 13. FLUTTER PAGINATION

Demonstrate:

```text
Offset pagination
Cursor pagination
Infinite scrolling
Pull to refresh
Load more
Pagination errors
Duplicate prevention
End-of-list handling
```

Use realistic repository/state architecture.

---

# 14. FLUTTER SEARCH

Demonstrate:

```text
Search
Debouncing
Filtering
Sorting
Server-side search
Local search
Search history
Empty results
Loading
Error
```

---

# 15. FLUTTER LOCAL STORAGE

Demonstrate appropriate local persistence patterns.

Examples:

```text
SharedPreferences
Secure storage
SQLite/Drift/Hive where justified
```

Use them for different use cases:

```text
Preferences
Secure credentials/tokens
Structured offline data
Caching
```

Explain why each storage mechanism is appropriate.

---

# 16. FLUTTER FILES

Demonstrate:

```text
File picker
Camera
Gallery
Image upload
Multiple files
Upload progress
Upload cancellation
Download
File preview
File validation
```

---

# 17. FLUTTER PUSH NOTIFICATIONS

Implement Firebase Cloud Messaging.

Demonstrate:

```text
Permission
Token registration
Token refresh
Foreground notification
Background notification
Notification tap
Deep linking from notification
Token invalidation
```

---

# 18. FLUTTER OFFLINE

Demonstrate:

```text
Connectivity detection
Local cache
Offline UI
Retry
Optimistic updates
Synchronization
Conflict handling
```

Do not pretend connectivity detection alone is offline support.

---

# 19. FLUTTER PERFORMANCE

Include examples/documentation for:

```text
const widgets
lazy lists
pagination
image caching
image resizing
rebuild optimization
isolates
debouncing
memoization where appropriate
controller disposal
resource lifecycle
```

Include examples of bad and improved implementations.

---

# 20. REACT + TYPESCRIPT REFERENCE IMPLEMENTATION

Create a separate React/TypeScript reference application.

Use a modern architecture.

Demonstrate:

```text
React
TypeScript
Routing
State management
API clients
Authentication
Forms
Validation
Data fetching
Caching
Error handling
Testing
Accessibility
Performance
```

---

# 21. REACT ROUTING

Demonstrate:

```text
Public routes
Protected routes
Nested routes
Dynamic routes
Route parameters
Query parameters
Redirects
404
Layouts
Navigation state
```

---

# 22. REACT AUTHENTICATION

Demonstrate an authentication architecture.

Include:

```text
Login
Register
Logout
Session restoration
Protected routes
Token handling
Refresh
User state
Permission state
```

Where Firebase is used, demonstrate:

```text
Email/password
Google
Phone where applicable
```

Separate:

```text
Auth Provider
Auth Service
Auth State
API authentication
Route protection
```

Do not put authentication logic throughout components.

---

# 23. REACT STATE MANAGEMENT

Demonstrate multiple categories:

```text
Local UI state
Global application state
Server state
Form state
URL state
```

Use appropriate technologies/patterns for each.

Demonstrate:

```text
React Context
Hooks
Server-state caching
Global state where justified
```

Do not use global state for everything.

---

# 24. REACT DATA FETCHING

Demonstrate:

```text
GET
POST
PUT
PATCH
DELETE
loading
error
empty
retry
pagination
infinite scrolling
cache
invalidate
optimistic update
```

Create a reusable API/data-access layer.

---

# 25. TYPESCRIPT

Demonstrate proper TypeScript patterns:

```text
Interfaces
Types
Generics
Unions
Discriminated unions
Utility types
Type guards
Enums where appropriate
API response types
Error types
Form types
Domain types
DTOs
```

Avoid:

```typescript
any
```

unless there is a documented reason.

---

# 26. REACT FORMS

Demonstrate:

```text
Login
Registration
Profile
Complex form
Multi-step form
Dynamic fields
File upload
Validation
Async validation
Server validation
```

---

# 27. REACT PERFORMANCE

Demonstrate:

```text
memoization
lazy loading
code splitting
virtualization
request caching
debouncing
throttling
avoiding unnecessary renders
image optimization
bundle optimization
```

Include examples of common performance mistakes.

---

# 28. DJANGO / PYTHON REFERENCE IMPLEMENTATION

Create a Django reference backend containing recurring backend patterns.

Demonstrate:

```text
Django
Django REST Framework
PostgreSQL
Authentication
Authorization
RBAC
API versioning
Serializers
Services
Repositories where useful
Queries
Transactions
Caching
Background tasks
File uploads
Emails
Webhooks
Testing
```

---

# 29. DJANGO API ARCHITECTURE

Demonstrate:

```text
Request
 ↓
URL
 ↓
View/ViewSet
 ↓
Serializer
 ↓
Service
 ↓
Repository/query layer where justified
 ↓
Model
 ↓
PostgreSQL
```

Do not blindly implement every layer for every endpoint.

Show when abstraction is justified.

---

# 30. DJANGO AUTHENTICATION

Demonstrate:

```text
User registration
Login
Logout
Password reset
Email verification
Token authentication
Session authentication
OAuth concepts
```

Where Firebase is used:

```text
Flutter
 ↓
Firebase Auth
 ↓
Firebase ID Token
 ↓
Django
 ↓
Firebase token verification
 ↓
Django user
```

Demonstrate how the backend should trust authentication without trusting arbitrary client-provided user IDs.

---

# 31. DJANGO AUTHORIZATION

Demonstrate:

```text
Permissions
Roles
RBAC
Object-level permissions
Ownership
Admin access
Staff access
```

Example:

```text
User
Manager
Admin
SuperAdmin
```

---

# 32. DJANGO DATABASE PATTERNS

Demonstrate:

```text
Models
Relationships
Indexes
Constraints
Transactions
select_related
prefetch_related
Annotations
Aggregations
Pagination
Soft deletion
Auditing
Migrations
```

Show common N+1 query mistakes and their solutions.

---

# 33. DJANGO TRANSACTIONS

Demonstrate:

```text
atomic transactions
select_for_update
idempotency
race conditions
concurrency
```

Use realistic examples such as:

```text
inventory
orders
payments
wallet balances
```

---

# 34. DJANGO CACHING

Demonstrate:

```text
Per-view caching
Low-level caching
Redis
Cache invalidation
TTL
Cache keys
Distributed caching
```

Explain:

> Cache invalidation is part of the architecture, not merely adding Redis.

---

# 35. BACKGROUND PROCESSING

Demonstrate:

```text
Celery
Redis
Workers
Scheduled tasks
Retries
Idempotency
Dead-letter/failure concepts
```

Use examples such as:

```text
Email
Notifications
Reports
Image processing
Third-party synchronization
```

---

# 36. DJANGO FILE UPLOADS

Demonstrate:

```text
Image uploads
Documents
Validation
Size limits
Storage abstraction
S3/Firebase Storage
Signed URLs
Deletion
```

---

# 37. WEBHOOKS

Create reusable webhook patterns.

Demonstrate:

```text
Signature verification
Idempotency
Event persistence
Retry
Async processing
Failure handling
```

Use payment webhook examples.

---

# 38. PAYMENT ENGINEERING

Create payment reference implementations.

Demonstrate the generic payment lifecycle:

```text
Created
Pending
Processing
Successful
Failed
Cancelled
Refunded
```

Demonstrate:

```text
Payment initiation
Provider response
Webhook
Verification
Idempotency
Transaction persistence
Reconciliation
```

Include provider adapters where practical:

```text
Stripe
M-Pesa
Airtel Money
```

Do not couple business logic directly to one provider.

---

# 39. SECURITY PATTERNS

Create a dedicated security section.

Demonstrate:

```text
Authentication
Authorization
Input validation
Rate limiting
CSRF
CORS
SQL injection prevention
XSS prevention
Secrets management
Secure headers
File validation
Password security
Token security
```

Also demonstrate common vulnerable patterns and corrected implementations.

---

# 40. OBSERVABILITY

Demonstrate:

```text
Structured logging
Request IDs
Error tracking
Metrics
Health checks
Readiness
Liveness
Tracing concepts
```

Explain what should be logged and what should never be logged.

---

# 41. TESTING

The repository must demonstrate testing at multiple levels.

Flutter:

```text
Unit
Widget
Integration
Golden where appropriate
```

React:

```text
Unit
Component
Integration
E2E
```

Django:

```text
Unit
Model
Service
API
Integration
Permission
Authentication
```

For important patterns, include both:

```text
Implementation
Test
```

---

# 42. ERROR HANDLING

Demonstrate a consistent error model across stacks.

For example:

```text
ValidationError
AuthenticationError
AuthorizationError
NotFoundError
ConflictError
RateLimitError
NetworkError
ExternalServiceError
UnknownError
```

Show how errors move through:

```text
Backend
 ↓
API
 ↓
Client
 ↓
State layer
 ↓
UI
```

---

# 43. API CONTRACTS

Create OpenAPI documentation.

Demonstrate:

```text
Request DTO
Response DTO
Error DTO
Pagination DTO
Authentication
Versioning
```

Where useful demonstrate generating TypeScript/Dart API types from OpenAPI.

---

# 44. CONFIGURATION

Demonstrate configuration for:

```text
Development
Testing
Staging
Production
```

Never hard-code secrets.

Demonstrate:

```text
.env
.env.example
secret management
Firebase configuration
API URLs
feature flags
```

---

# 45. CI/CD

Create examples for:

```text
Flutter CI
React CI
Django CI
TypeScript checks
Python checks
Unit tests
Integration tests
Builds
Docker builds
Security scanning
Deployment
```

---

# 46. DOCKER

Create reusable Docker patterns for:

```text
Django
PostgreSQL
Redis
Celery
React
Nginx
```

Only include services where they demonstrate a meaningful pattern.

---

# 47. SOFTWARE DESIGN PATTERNS

Create examples of commonly useful patterns:

```text
Repository
Service
Factory
Strategy
Adapter
Observer
Dependency Injection
State
Command
Builder
Facade
Decorator
```

But do NOT implement design patterns simply to demonstrate them.

For every pattern explain:

```text
Problem
Pattern
Implementation
Why it helps
When NOT to use it
```

---

# 48. ARCHITECTURAL PATTERNS

Demonstrate:

```text
Layered architecture
Clean architecture
Feature-based architecture
Repository pattern
Service layer
Event-driven concepts
Modular monolith
Microservice boundaries
```

The reference codebase should show the difference between:

```text
Good abstraction
vs
Over-engineering
```

---

# 49. COMMON ENGINEERING PROBLEMS

Create a section called:

```text
common-problems/
```

Include examples of:

```text
N+1 queries
Race conditions
Duplicate requests
Double payments
Memory leaks
Unnecessary Flutter rebuilds
React unnecessary renders
Stale cache
Token expiration
Network timeout
Partial failure
Retry storms
Large payloads
Slow images
Large lists
Unvalidated input
Authorization bugs
```

For every problem show:

```text
Bad implementation
Why it fails
Improved implementation
Tests
```

---

# 50. DOCUMENTATION REQUIREMENT

Every pattern must have documentation.

Use:

```text
README.md
```

inside each pattern directory.

Each README should explain:

```text
What problem does this solve?
When is this pattern useful?
How does it work?
What are the trade-offs?
What are common mistakes?
How do I adapt it to a real project?
```

---

# 51. DO NOT MAKE EVERYTHING ABSTRACT

This is extremely important.

Do not create:

```text
AbstractBaseRepository
BaseService
BaseController
GenericManager
UniversalProvider
UniversalFactory
```

simply because they sound architectural.

Abstraction must solve a real recurring problem.

The purpose of this repository is to teach **good engineering judgment**, not to maximize abstraction.

---

# 52. DEMONSTRATION APPLICATIONS

Build small demonstration features around the patterns.

For example:

```text
Authentication Demo
CRUD Demo
Pagination Demo
Search Demo
File Upload Demo
Notification Demo
Payment Demo
Realtime Demo
Offline Demo
Form Demo
Authorization Demo
Caching Demo
```

These demos should be intentionally small.

They exist to demonstrate engineering patterns, not product functionality.

---

# 53. CROSS-STACK COMPARISON

For every major engineering concern create documentation like:

```text
Authentication

Flutter
    Firebase Auth + Riverpod

React
    Firebase Auth + Context/Provider

Django
    Token verification + permissions

FastAPI
    Dependency-based authentication
```

Then explain:

```text
What stays the same conceptually?
What changes because of the ecosystem?
What are the trade-offs?
```

This is a critical requirement.

---

# 54. ENGINEERING PRINCIPLES

Create a documentation section covering:

```text
SOLID
DRY
KISS
YAGNI
Separation of concerns
Composition over inheritance
Dependency inversion
Single responsibility
Fail fast
Defensive programming
Idempotency
Immutability where useful
Explicit over implicit
```

Do not merely define them.

Show working code examples.

---

# 55. SOFTWARE LIFECYCLE

Document the complete lifecycle:

```text
Idea
 ↓
Requirements
 ↓
Architecture
 ↓
Data modelling
 ↓
API contract
 ↓
Implementation
 ↓
Testing
 ↓
CI
 ↓
Deployment
 ↓
Monitoring
 ↓
Maintenance
 ↓
Refactoring
 ↓
Retirement
```

Demonstrate engineering practices associated with each stage.

---

# 56. PROJECT QUALITY GATE

Create automated checks for:

```text
Formatting
Linting
Type checking
Tests
Build
Dependency checks
Security checks
```

The reference repository itself should demonstrate how a professional project enforces quality.

---

# 57. FINAL REPOSITORY STRUCTURE

Aim for something conceptually similar to:

```text
software-engineering-reference/
│
├── README.md
│
├── docs/
│   ├── architecture/
│   ├── engineering-principles/
│   ├── patterns/
│   ├── security/
│   ├── performance/
│   └── deployment/
│
├── flutter/
│   ├── reference_app/
│   └── patterns/
│
├── react/
│   ├── reference_app/
│   └── patterns/
│
├── django/
│   ├── reference_api/
│   └── patterns/
│
├── fastapi/
│   └── reference_api/
│
├── infrastructure/
│   ├── docker/
│   ├── github-actions/
│   └── deployment/
│
├── examples/
│   ├── authentication/
│   ├── payments/
│   ├── notifications/
│   ├── pagination/
│   ├── uploads/
│   ├── caching/
│   ├── webhooks/
│   └── realtime/
│
└── scripts/
```

Adapt the structure if a better organization emerges.

---

# 58. IMPORTANT: DO NOT IMPLEMENT EVERYTHING IN ONE PASS

Work incrementally.

First produce:

1. Pattern catalogue
2. Repository architecture
3. Technology choices
4. Implementation roadmap

Then implement foundations.

Then implement patterns category by category.

After each major category:

```text
Run tests
Run lint
Run type checks
Verify builds
Update documentation
```

Do not continue accumulating broken code.

---

# 59. QUALITY OF THE REFERENCE IMPLEMENTATION

Every implementation must be:

```text
Real
Runnable
Tested
Documented
Adaptable
Reasonably production-quality
```

Do not create pseudo-code where working code is expected.

Do not create placeholder functions such as:

```text
TODO
throw UnimplementedError()
pass
return null
```

for core demonstrations.

---

# 60. FINAL OBJECTIVE

When this repository is complete, I should be able to start a new project and think:

> "I need authentication."

I can look here.

> "I need Firebase Google + Email + Phone authentication with Riverpod."

I can look here.

> "I need routing and protected routes."

I can look here.

> "I need pagination."

I can look here.

> "I need a Django service layer."

I can look here.

> "I need React authentication."

I can look here.

> "I need a TypeScript API client."

I can look here.

> "I need file uploads."

I can look here.

> "I need M-Pesa payments."

I can look here.

> "I need webhooks."

I can look here.

> "I need Redis caching."

I can look here.

> "I need background jobs."

I can look here.

> "I need offline Flutter."

I can look here.

> "I need CI/CD."

I can look here.

The repository should become my **personal software engineering reference implementation and reusable foundation**.

Do not optimize for the number of files.

Optimize for the number of **important recurring engineering problems solved correctly**.

Start by inspecting the environment/repository and produce the **complete engineering pattern catalogue and proposed repository architecture** before implementing the code.
