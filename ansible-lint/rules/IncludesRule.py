"""Rule definition for usage of include_* that could be import_tasks or vars_files."""
from typing import TYPE_CHECKING, Any, Dict, Union

from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from typing import Optional

INCLUDE_MODULES = {
    "ansible.builtin.include_tasks": "Should be import_tasks",
    "ansible.builtin.include_vars": "Should be vars_files in the play parameters"
}

class IncludesRule(AnsibleLintRule):
    id = "includes"
    shortdesc = "Shouldn't be include_*"
    description = "Check whether an include_* action uses a loop or is templated"
    tags = ["idiom", "custom"]

    def matchtask(
        self, task: Dict[str, Any], file: 'Optional[Lintable]' = None
    ) -> Union[bool,str]:
        if task["action"]["__ansible_module_original__"] not in (INCLUDE_MODULES):
            return False

        if not self.task_has_loop(task) and not self.task_has_templated_args(task):
            return INCLUDE_MODULES[task["action"]["__ansible_module_original__"]]
        else:
            return False

    def task_has_loop(self, task: Dict[str, Any]):
        for key in task.keys():
            if key == "loop" or key.startswith("with_"):
                return True
        return False

    def task_has_templated_args(self, task: Dict[str, Any]):
        if task["action"]["__ansible_arguments__"] and "{{" in task["action"]["__ansible_arguments__"][0]:
            return True
        elif "file" in task["action"] and "{{" in task["action"]["file"]:
            return True
        else:
            return False
