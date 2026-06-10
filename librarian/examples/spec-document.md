---
title: API Authentication Design
type: spec
spec_type: api-design
created: 2026-06-08T09:00:00Z
updated: 2026-06-09T11:15:00Z
tags: ["api", "auth", "jwt", "security"]
scope: project
---

<!-- Stored at: projects/<YYYY_MM_DD_slug>/specs/api-design.md
     Written via: librarian.py spec write api-design --file draft.md -->


# API Authentication Design

## Overview

This spec defines the authentication strategy for the REST API.

## Decision

Use JWT tokens with short expiry (15 min) and refresh tokens (7 days).

## Endpoints

- `POST /auth/login` — exchange credentials for token pair
- `POST /auth/refresh` — exchange refresh token for new access token
- `POST /auth/logout` — invalidate refresh token

## Token Format

Access tokens: JWT with `sub`, `exp`, `iat`, `role` claims.
Refresh tokens: Opaque random string stored in database.