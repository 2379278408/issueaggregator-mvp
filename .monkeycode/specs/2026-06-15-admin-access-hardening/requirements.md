# Requirements Document

## Introduction

本功能用于升级 Issue Aggregator 的后台访问安全能力。当前系统使用共享 `X-Admin-Token` 和固定 `/admin` 路由完成后台访问控制，已经具备最小可用能力。下一阶段需要把后台访问升级为管理员账号密码登录、服务端会话控制和环境配置驱动的随机后台路由，以提升后台身份校验强度、降低静态凭证暴露风险、收紧会话生命周期，并减少通用扫描对后台入口的直接命中。

本次范围聚焦单管理员场景，保留现有审计、限流和管理工作台主流程。

## Glossary

- **System**: Issue Aggregator 前后端系统。
- **Administrator**: 允许访问后台工作台的管理人员。
- **Admin Session**: 由服务端创建、带过期时间、可撤销的后台登录会话。
- **Admin Route Slug**: 由环境配置提供的后台前端路由片段。
- **Admin API Namespace**: 由环境配置提供的后台 API 命名空间。
- **Session Cookie**: 由服务端签发并由浏览器自动携带的后台认证 Cookie。

## Requirements

### Requirement 1

**User Story:** AS an Administrator, I want to sign in with an account and password, so that the backend can verify my identity with stronger credentials.

#### Acceptance Criteria

1. WHEN an Administrator submits a valid username and password, the System SHALL create one active Admin Session.
2. WHEN the System creates an Admin Session, the System SHALL return the session through a secure cookie-based mechanism.
3. IF an Administrator submits an invalid username or password, the System SHALL reject the login attempt and record one authentication failure audit event.
4. WHEN an Administrator signs in successfully, the System SHALL return the Administrator profile summary required by the backend workspace.

### Requirement 2

**User Story:** AS an Administrator, I want the backend session to expire automatically, so that dormant browser state does not hold indefinite backend access.

#### Acceptance Criteria

1. WHILE an Admin Session is active, the System SHALL allow access to protected backend APIs.
2. WHEN an Admin Session exceeds the configured idle timeout, the System SHALL mark the Admin Session as expired.
3. WHEN an Admin Session exceeds the configured absolute lifetime, the System SHALL mark the Admin Session as expired.
4. IF a protected backend API receives an expired or unknown Admin Session, the System SHALL reject the request and record one authentication failure audit event.
5. WHEN an Administrator triggers sign-out, the System SHALL revoke the current Admin Session and clear the session cookie.

### Requirement 3

**User Story:** AS a project owner, I want login failures to be rate-limited and auditable, so that the backend can slow repeated guessing attempts and preserve review evidence.

#### Acceptance Criteria

1. WHEN repeated login failures from the same client exceed the configured threshold within the configured window, the System SHALL apply a temporary login cooldown.
2. WHILE a login cooldown is active for one client, the System SHALL reject new login attempts from that client.
3. WHEN the System rejects a login attempt because of cooldown, the System SHALL record one authentication failure audit event with the cooldown reason.
4. WHEN the System accepts a login attempt, the System SHALL record one authentication success audit event.
5. WHEN the System revokes or expires an Admin Session, the System SHALL preserve timestamps required for later review.

### Requirement 4

**User Story:** AS a project owner, I want backend routes to use environment-configured random path segments, so that automated scanners have less direct signal about the admin entry points.

#### Acceptance Criteria

1. WHEN the System starts, the System SHALL load the Admin Route Slug and Admin API Namespace from environment configuration.
2. WHEN the frontend registers the backend workspace route, the System SHALL expose the workspace at `/<Admin Route Slug>`.
3. WHEN the backend registers protected admin APIs, the System SHALL expose the APIs at `/api/admin/<Admin API Namespace>`.
4. IF the Admin Route Slug or Admin API Namespace is absent or invalid in a production environment, the System SHALL fail startup with a configuration error.
5. WHEN a browser accesses a stale backend route path, the System SHALL resolve the request through the public router behavior and preserve the hidden backend route policy.

### Requirement 5

**User Story:** AS an Administrator, I want the frontend backend workspace to restore my authenticated state safely, so that I can continue work without re-entering credentials on every navigation.

#### Acceptance Criteria

1. WHEN the backend workspace page loads, the System SHALL query the current Admin Session state from the backend.
2. IF the browser holds a valid Admin Session cookie, the System SHALL unlock the backend workspace without requesting a token in page state.
3. IF the browser does not hold a valid Admin Session cookie, the System SHALL present the backend sign-in form.
4. WHEN the frontend sends protected backend API requests, the System SHALL rely on browser cookie transport instead of custom token headers.
5. WHEN the backend workspace receives an authentication failure response, the System SHALL reset the local unlocked state and present the sign-in form.

### Requirement 6

**User Story:** AS a project owner, I want existing backend operations to remain available after the authentication upgrade, so that the security change does not break draft review and submission workflows.

#### Acceptance Criteria

1. WHEN an Administrator completes sign-in, the System SHALL allow the existing feedback queue, batch creation, draft integration, draft update, submission, and audit queries through the new Admin Session.
2. WHEN the System migrates from token-based backend access to session-based backend access, the System SHALL preserve the existing audit event categories and operation logging behavior.
3. WHEN the frontend or backend is configured for local development, the System SHALL support an explicit development-safe configuration path for Admin Route Slug, Admin API Namespace, and session secrets.
4. WHEN the System applies the authentication upgrade, the System SHALL preserve the public feedback page and submitted issue queries without requiring backend login.

## Operational Constraints

- 单管理员是本轮默认角色模型。
- 密码只允许以摘要形式持久化。
- 会话密钥、管理员密码摘要、后台路由配置只允许来自服务端环境变量或服务端安全存储。
- 随机后台路由用于降低入口暴露噪声，后台访问控制由登录态校验承担。

## Out of Scope

- 多管理员角色分级。
- TOTP、WebAuthn、短信或邮件验证码。
- SSO、OAuth、LDAP 或外部身份提供方。
- 设备信任列表和异地登录识别。
