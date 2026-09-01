"""Paperforge document build and publication pipeline."""

# The version the *pipeline* knows about, as distinct from the two that
# describe the plugin around it. The bundle ships `bin/`, `paperforge/` and
# `tests/` and neither `realtimex.plugin.json` nor `SKILL.md`, so an installed
# pipeline cannot read either of them - and something has to be able to say
# what a project was scaffolded by.
#
# Three copies of one number is two chances to drift, which is why
# `package_plugin.version_problems` holds all three to the same value and the
# release refuses a tag that disagrees.
__version__ = '4.0.0'
