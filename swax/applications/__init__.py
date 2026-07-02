"""Application use-cases and their aggregator facade.

The facade is built incrementally: task 16 adds the init use-case cell, task 17
adds the discover use-case cell, and task 18 wires this package to re-export
both handlers (run_init_handler, run_discover_handler).
"""
