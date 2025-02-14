# Copyright 2018 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for the PythonExpression substitution."""

import collections.abc
import importlib
from typing import List
from typing import Sequence
from typing import Text

from ..frontend import expose_substitution
from ..launch_context import LaunchContext
from ..some_substitutions_type import SomeSubstitutionsType
from ..substitution import Substitution
from ..utilities import ensure_argument_type


@expose_substitution('eval')
class PythonExpression(Substitution):
    """
    Substitution that can access contextual local variables.

    The expression may contain Substitutions, but must return something that can
    be converted to a string with `str()`.
    It also may contain math symbols and functions.
    """

    def __init__(self, expression: SomeSubstitutionsType,
                 python_modules: SomeSubstitutionsType = ['math']) -> None:
        """Create a PythonExpression substitution."""
        super().__init__()

        ensure_argument_type(
            expression,
            (str, Substitution, collections.abc.Iterable),
            'expression',
            'PythonExpression')

        ensure_argument_type(
            python_modules,
            (str, Substitution, collections.abc.Iterable),
            'python_modules',
            'PythonExpression')

        from ..utilities import normalize_to_list_of_substitutions
        self.__expression = normalize_to_list_of_substitutions(expression)
        self.__python_modules = normalize_to_list_of_substitutions(python_modules)

    @classmethod
    def parse(cls, data: Sequence[SomeSubstitutionsType]):
        """Parse `PythonExpression` substitution."""
        if len(data) < 1 or len(data) > 2:
            raise TypeError('eval substitution expects 1 or 2 arguments')
        kwargs = {}
        kwargs['expression'] = data[0]
        if len(data) == 2:
            # We get a text substitution from XML,
            # whose contents are comma-separated module names
            kwargs['python_modules'] = []
            # Check if we got empty list from XML
            # Ensure that we got a list!
            assert not isinstance(data[1], str)
            assert not isinstance(data[1], Substitution)
            # Modules
            modules = list(data[1])
            if len(modules) > 0:
                # XXX: What is going on here: the type annotation says we should get
                # a either strings or substitutions, but this says that we're
                # getting a substitution always?
                # Moreover, `perform` is called with `None`, which is not acceptable
                # for any substitution as far as I know (should be an empty launch context?)
                modules_str = modules[0].perform(None)  # type: ignore
                kwargs['python_modules'] = [module.strip() for module in modules_str.split(',')]
        return cls, kwargs

    @property
    def expression(self) -> List[Substitution]:
        """Getter for expression."""
        return self.__expression

    @property
    def python_modules(self) -> List[Substitution]:
        """Getter for expression."""
        return self.__python_modules

    def describe(self) -> Text:
        """Return a description of this substitution as a string."""
        return 'PythonExpr({}, [{}])'.format(
            ' + '.join([sub.describe() for sub in self.expression]),
            ', '.join([sub.describe() for sub in self.python_modules]))

    def perform(self, context: LaunchContext) -> Text:
        """Perform the substitution by evaluating the expression."""
        from ..utilities import perform_substitutions
        module_names = [context.perform_substitution(sub) for sub in self.python_modules]
        module_objects = [importlib.import_module(name) for name in module_names]
        expression_locals = {}
        for module in module_objects:
            # For backwards compatility, we allow math definitions to be implicitly
            # referenced in expressions, without prepending the math module name
            # TODO: This may be removed in a future release.
            if module.__name__ == 'math':
                expression_locals.update(vars(module))

            expression_locals[module.__name__] = module
        return str(eval(perform_substitutions(context, self.expression), {}, expression_locals))
