# Verified Sourcing Layer - 2026-06-09

## Purpose

This document defines the internal sourcing discipline for DueSight launch materials. It is a working layer for evidence handling and claim control.

It does not certify sources and does not authorize public claims. It tells agents how to keep source-backed work separated from assumptions.

## Source States

| State | Meaning | Public use |
| --- | --- | --- |
| VERIFIED | The source is reachable, relevant, and recorded with enough detail to review later. | May support careful copy after owner approval. |
| PARTIAL | The source supports part of the claim, but not the whole conclusion. | Do not use as a standalone public claim. |
| NEEDS_CHECK | The source or interpretation still needs manual review. | Internal only. |
| DO_NOT_USE | The source is broken, irrelevant, stale, or creates legal/commercial risk. | Never use in public copy. |

## Required Evidence Fields

Every launch-critical source note should record:

- source title or system name,
- source URL or local file path,
- date checked,
- what exact point it supports,
- limitation or caveat,
- owner who can approve public use.

## Public-Copy Rules

- Avoid fixed source-count claims unless a maintained source inventory proves them.
- Avoid vendor, model, and provider disclosure in public copy.
- Avoid compliance-status claims unless counsel signs off.
- Avoid named competitor comparisons unless evidence and legal review both support them.
- Prefer cautious language: "public-source based", "source-backed", "documented", "review-ready".

## Agent Checklist

Before any source-backed claim enters a staged set:

- Confirm the source state is VERIFIED.
- Confirm the claim says no more than the source supports.
- Confirm the wording passes the public surface gate where relevant.
- Confirm owner/legal review is not required first.
- If uncertain, leave the claim out and report it as [BESLISSING].

## Commit Readiness

This file is safe for the finalize documentation commit. It changes no website, payment, or public runtime behavior.
