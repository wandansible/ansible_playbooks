"""Rule definition for usage of tasks without a name."""
from typing import TYPE_CHECKING, Any, Dict, Union

from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from typing import Optional

IGNORE = [
    "ansible.builtin.import_tasks",
    "ansible.builtin.include_tasks",
    "ansible.builtin.set_fact",
    "block/always/rescue"
]

class TaskHasNameRule(AnsibleLintRule):
    id = "task-unnamed"
    shortdesc = "All tasks should be named"
    description = "All tasks should have a distinct name for readability " \
        "and for ``--start-at-task`` to work. Ignores: " + ", ".join(IGNORE)
    tags = ["idiom", "custom"]

    def matchtask(
        self, task: Dict[str, Any], file: 'Optional[Lintable]' = None
    ) -> Union[bool,str]:
        if task["action"]["__ansible_module_original__"] in IGNORE:
            return False
        return "name" not in task
