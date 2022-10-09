"""Rule definition for usage of systemd that could be service."""
from typing import TYPE_CHECKING, Any, Dict, Union

from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from typing import Optional

class SystemdRule(AnsibleLintRule):
    id = "systemd"
    shortdesc = "Should be ansible.builtin.service"
    description = "Check whether an ansible.builtin.systemd action uses variables specific to systemd"
    tags = ["idiom", "custom"]

    def matchtask(
        self, task: Dict[str, Any], file: 'Optional[Lintable]' = None
    ) -> Union[bool,str]:
        if task["action"]["__ansible_module_original__"] != "ansible.builtin.systemd":
            return False

        for key in task["action"].keys():
            if key in (
                "daemon_reexec",
                "daemon_reload",
                "masked",
                "scope"):
                return False
        return True
