"""Rule definition for usage of environment variables for all playbooks."""
from typing import TYPE_CHECKING, Any, List

from ansiblelint.errors import MatchError
from ansiblelint.file_utils import Lintable
from ansiblelint.rules import AnsibleLintRule
from ansiblelint.utils import LINE_NUMBER_KEY

if TYPE_CHECKING:
    from ansiblelint.constants import odict

class EnvironmentVarsRule(AnsibleLintRule):
    id = "environment-vars"
    shortdesc = "Set environment variables for all playbooks"
    description = "Check whether playbooks have set ``environment`` at the play level"
    tags = ["idiom", "custom"]

    def matchplay(
        self, file: Lintable, data: "odict[str, Any]"
    ) -> List[MatchError]:
        """Return matches found for a specific playbook."""

        if file.kind != "playbook":
            return []

        if "import_playbook" not in data and "environment" not in data:
            if "name" in data:
                details = "Playbook: " + data["name"]
            else:
                details = "Playbook"
            return [self.create_matcherror(
                    filename=file,
                    linenumber=data[LINE_NUMBER_KEY],
                    details=details)]
        return []
