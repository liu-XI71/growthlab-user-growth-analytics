# Security and privacy policy

## Supported version

The latest `main` branch is the supported public-demo version.

## Reporting a vulnerability

Please use GitHub's private vulnerability-reporting feature when available. Do not open a public issue containing credentials, personal data, exploit details against a live service, or confidential business information.

## Public-demo threat boundary

GrowthLab is a local portfolio application and is not hardened as a multi-tenant production service. The public demo includes:

- request validation and governed dimension whitelists;
- parameterized database queries for user-controlled values;
- no production credentials or cloud requirement;
- synthetic identifiers and normalized economics;
- automated secret, sensitive-marker and large-file checks;
- read-only analytical database access during API queries;
- restricted local CORS origins.

A production deployment would additionally require authentication and authorization, a managed secrets store, TLS termination, centralized audit logs, rate limiting, dependency and container scanning, backup/retention policy, user-level privacy controls, and a governed warehouse rather than a local embedded database.
