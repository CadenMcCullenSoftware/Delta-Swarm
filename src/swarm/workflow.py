"""Workflow definition: tasks, dependencies, and execution order."""

from __future__ import annotations

from .types import Task, TaskStatus


class Workflow:
    """A collection of tasks with dependency relationships."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._tasks: dict[str, Task] = {}
        self._order: list[str] = []

    def add_task(self, task: Task) -> None:
        self._tasks[task.task_id] = task
        self._order = []

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def tasks(self) -> dict[str, Task]:
        return dict(self._tasks)

    def dependency_order(self) -> list[str]:
        """Return task ids in topological dependency order."""
        if self._order:
            return list(self._order)
        visited: set[str] = set()
        order: list[str] = []
        visiting: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            if task_id in visiting:
                raise ValueError(f"Circular dependency detected at {task_id}")
            visiting.add(task_id)
            task = self._tasks[task_id]
            for dep in task.depends_on:
                if dep not in self._tasks:
                    raise ValueError(f"Task {task_id} depends on unknown task {dep}")
                visit(dep)
            visiting.discard(task_id)
            visited.add(task_id)
            order.append(task_id)

        for task_id in self._tasks:
            visit(task_id)

        self._order = order
        return list(order)

    def ready_tasks(self) -> list[Task]:
        """Return pending tasks whose dependencies are complete."""
        ready: list[Task] = []
        completed = {
            tid for tid, t in self._tasks.items() if t.status == TaskStatus.COMPLETED
        }
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if all(dep in completed for dep in task.depends_on):
                ready.append(task)
        return ready

    def mark(self, task_id: str, status: TaskStatus,
             result: str | None = None, error: str | None = None,
             assigned_to: str | None = None) -> None:
        task = self._tasks[task_id]
        task.status = status
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        if assigned_to is not None:
            task.assigned_to = assigned_to
