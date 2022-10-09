"""Rule definition for usage of fully qualified collection names for all modules."""
import re
from typing import TYPE_CHECKING, Any, Dict, List, Union

from ansiblelint.errors import MatchError
from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule
from ansiblelint.utils import LINE_NUMBER_KEY

if TYPE_CHECKING:
    from typing import Optional

    from ansiblelint.constants import odict

FQCN_REGEX = '^\w+\.\w+\.\w+$'

IGNORE = [
    "block/always/rescue"
]

class FQCNModulesRule(AnsibleLintRule):
    id = "fqcn-modules"
    shortdesc = "Use FQCN for all actions"
    description = "Check whether the actions in playbooks are using FQCN for all modules"
    tags = ["formatting", "custom"]

    def __init__(self) -> None:
        """Save precompiled regex."""
        self.fqcn_regex = re.compile(FQCN_REGEX)

    def matchtask(
        self, task: Dict[str, Any], file: 'Optional[Lintable]' = None
    ) -> Union[bool,str]:
        if task["action"]["__ansible_module__"] in IGNORE:
            return False

        return not self.fqcn_regex.match(task["action"]["__ansible_module_original__"])

    def matchplay(
        self, file: Lintable, data: "odict[str, Any]"
    ) -> List[MatchError]:
        """Return matches found for a specific playbook."""
        results: List[MatchError] = []

        if file.kind not in ('tasks', 'pre_tasks', 'post_tasks', 'handlers', 'playbook'):
            return results

        if file.kind == "playbook":
            for tasks_tag in ('tasks', 'pre_tasks', 'post_tasks'):
                if tasks_tag in data:
                    results.extend(self.handle_tasks(file, data[tasks_tag]))
        else:
            results.extend(self.handle_play(file, data))

        return results

    def handle_play(
        self, lintable: Lintable, task: "odict[str, Any]"
    ) -> List[MatchError]:
        """Return matches for a playlist."""
        results = []
        if 'block' in task:
            results.extend(self.handle_tasks(lintable, task['block']))
        else:
            results.extend(self.handle_task(lintable, task))
        return results

    def handle_tasks(
        self, lintable: Lintable, tasks: List["odict[str, Any]"]
    ) -> List[MatchError]:
        """Return matches for a list of tasks."""
        results = []
        for play in tasks:
            results.extend(self.handle_play(lintable, play))
        return results

    def handle_task(
        self, lintable: Lintable, task: "odict[str, Any]"
    ) -> List[MatchError]:
        """Return matches for a specific task."""
        for key in task.keys():
            if key in ('import_tasks', 'include_tasks'):
                details = "Task/Handler: "
                if "name" in task:
                    details += task['name']
                else:
                    details += key
                return [self.create_matcherror(
                    filename=lintable,
                    linenumber=task[LINE_NUMBER_KEY],
                    details=details)]
        return []
