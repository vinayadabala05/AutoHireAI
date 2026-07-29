"""Business/domain logic layer.

Services orchestrate one or more repositories (and, later, agents) to
fulfill a use case. API routers stay thin and call into services rather
than embedding business logic in the request handler.
"""
