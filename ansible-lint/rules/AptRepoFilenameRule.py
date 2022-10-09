"""Rule definition for usage of filename for apt_repository."""
from typing import TYPE_CHECKING, Any, Dict, Union

from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule

if TYPE_CHECKING:
    from typing import Optional

class AptRepoFilenameRule(AnsibleLintRule):
    id = "apt-repo-filename"
    shortdesc = "All apt_repository tasks should set filename"
    description = "All ``ansible.builtin.apt_repository`` tasks should set ``filename`` " \
        "to avoid getting the auto-generated filename based on a URL"
    tags = ["idiom", "custom"]

    def matchtask(
        self, task: Dict[str, Any], file: 'Optional[Lintable]' = None
    ) -> Union[bool,str]:
        if task["action"]["__ansible_module_original__"] != "ansible.builtin.apt_repository":
            return False

        if "state" in task["action"] and task["action"]["state"] == "absent":
            return False

        return "filename" not in task["action"]
