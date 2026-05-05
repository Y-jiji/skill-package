---
name: unit-test
description: Unit testing conventions. Fuzz/property-based testing by default, split into correctness and performance categories.
---

# Unit Testing

- Fuzz/property-based by default, example-based only for hard-to-reach cases.
- Split into correctness tests and performance tests.
- Test all public methods in all possible call orders.
- Create a mock/reference implementation to test against.
