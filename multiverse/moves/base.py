import re
from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, ClassVar, Generic, TYPE_CHECKING
from dataclasses import dataclass, fields

if TYPE_CHECKING:
    from multiverse.agent import Agent
    from multiverse.environment import Environment


class InvalidMoveSyntax(Exception):
    """Raised when a command string is not formatted according to a known Move type"""


class InvalidMoveValue(Exception):
    """Raised when a command string is formatted correctly, but has invalid parsed components"""


T = TypeVar("T", bound="MoveParameters")


@dataclass
class MoveParameters(ABC):
    content: str


@dataclass
class MoveOutcome(ABC):
    params: Type[T]
    response: str


class Move(ABC, Generic[T]):
    name: ClassVar[str]
    parameters_class: ClassVar[Type[T]]
    template: ClassVar[str] = r"<{move_name}{spacing}{params}>{content}</{move_name}>"

    @classmethod
    def get_request_syntax(self) -> str:
        param_fields = [f for f in fields(self.parameters_class) if f.name != "content"]
        param_patterns = " ".join(
            f'{f.name}="(?P<{f.name}>[^"]+)"' for f in param_fields
        )
        spacing = " " if param_patterns else ""
        return self.template.format(
            move_name=self.name.lower(),
            spacing=spacing,
            params=param_patterns,
            content=r"(?P<content>[\s\S]+)",
        )

    @classmethod
    def parse(cls, command: str) -> Optional[T]:
        match = re.match(cls.get_request_syntax(), command)
        if match:
            return cls.parameters_class(**match.groupdict())
        return None

    @abstractmethod
    def validate(self, agent: "Agent", params: T, environment: "Environment"):
        pass

    @abstractmethod
    def execute(
        self, agent: "Agent", params: T, environment: "Environment"
    ) -> MoveOutcome:
        pass
