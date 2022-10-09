"""Rule definition for usage of apt_key that should set keyring."""
from typing import TYPE_CHECKING, Any, Dict, Union

from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from typing import Optional

class AptKeyringRule(AnsibleLintRule):
    id = "apt-keyring"
    shortdesc = "keyring should be set and stored under /etc/apt/keyrings"
    description = "Check whether an ansible.builtin.apt_key action sets ``keyring``. " \
        "The key must also be stored under /etc/apt/keyrings."
    tags = ["idiom", "custom"]

    def matchtask(
        self, task: Dict[str, Any], file: 'Optional[Lintable]' = None
    ) -> Union[bool,str]:
        if task["action"]["__ansible_module_original__"] != "ansible.builtin.apt_key":
            return False

        if "state" in task["action"] and task["action"]["state"] == "absent":
            return False

        return not "keyring" in task["action"] or \
            not task["action"]["keyring"].startswith("/etc/apt/keyrings/") and \
            "{{" not in task["action"]["keyring"]
