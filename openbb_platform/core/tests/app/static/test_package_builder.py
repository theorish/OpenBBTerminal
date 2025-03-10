"""Test the package_builder.py file."""
# pylint: disable=redefined-outer-name, protected-access

from dataclasses import dataclass
from inspect import _empty
from pathlib import Path
from unittest.mock import PropertyMock, mock_open, patch

import pandas
import pytest
from importlib_metadata import EntryPoint, EntryPoints
from openbb_core.app.static.package_builder import (
    ClassDefinition,
    DocstringGenerator,
    ImportDefinition,
    MethodDefinition,
    ModuleBuilder,
    PackageBuilder,
    Parameter,
    PathHandler,
)
from openbb_core.env import Env
from pydantic import Field
from typing_extensions import Annotated


@pytest.fixture(scope="module")
def tmp_package_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("package")


@pytest.fixture(scope="module")
def package_builder(tmp_package_dir):
    """Return package builder."""
    return PackageBuilder(tmp_package_dir)


def test_package_builder_init(package_builder):
    """Test package builder init."""
    assert package_builder


def test_package_builder_build(package_builder):
    """Test package builder build."""
    package_builder.build()


def test_save_module_map(package_builder):
    """Test save module map."""
    package_builder._save_module_map()


def test_save_modules(package_builder):
    """Test save module."""
    package_builder._save_modules()


def test_save_package(package_builder):
    """Test save package."""
    package_builder._save_package()


def test_run_linters(package_builder):
    """Test run linters."""
    package_builder._run_linters()


def test_write(package_builder):
    """Test save to package."""
    package_builder._write(code="", name="test", extension="json")


@pytest.fixture(scope="module")
def module_builder():
    """Return module builder."""
    return ModuleBuilder()


def test_module_builder_init(module_builder):
    """Test module builder init."""
    assert module_builder


@pytest.fixture(scope="module")
def class_definition():
    """Return class definition."""
    return ClassDefinition()


def test_class_definition_init(class_definition):
    """Test class definition init."""
    assert class_definition


def test_build(class_definition):
    """Test build."""
    code = class_definition.build("openbb_core.app.static.container.Container")
    assert code


@pytest.fixture(scope="module")
def method_definition():
    """Return method definition."""
    return MethodDefinition()


def test_method_definition_init(method_definition):
    """Test method definition init."""
    assert method_definition


def test_build_class_loader_method(method_definition):
    """Test build class loader method."""
    code = method_definition.build_class_loader_method(
        "openbb_core.app.static.container.Container"
    )
    assert code


def test_get_type(method_definition):
    """Test get type."""
    type_ = method_definition.get_type(field=Parameter.empty)
    assert type_
    assert isinstance(type_, type)


def test_get_type_hint(method_definition):
    """Test get type hint."""

    class TestField:
        annotation = int

    field = TestField()
    result = method_definition.get_type(field)
    assert result == int


def test_field_with_type_attribute_missing_type(method_definition):
    """Test field with type attribute missing type."""

    class TestField:
        annotation = Parameter.empty

    field = TestField()
    result = method_definition.get_type(field)
    assert result is _empty


def test_get_default(method_definition):
    """Test get default."""

    class TestField:
        default = Field(default=42)

    field = TestField()
    result = method_definition.get_default(field)
    assert result == 42


def test_get_default_none(method_definition):
    """Test get default."""

    class TestField:
        default = 42

    field = TestField()
    result = method_definition.get_default(field)
    assert result is None


def test_get_default_default_value(method_definition):
    """Test get default default value."""

    class TestField:
        default = type(Ellipsis)()

    field = TestField()
    result = method_definition.get_default(field)
    assert result is None


def test_get_default_no_default(method_definition):
    """Test get default no default."""

    class TestField:
        pass

    field = TestField()
    result = method_definition.get_default(field)
    assert result == _empty


def test_is_annotated_dc(method_definition):
    """Test is annotated dc."""
    result = method_definition.is_annotated_dc(annotation=Parameter.empty)
    assert not result


def test_is_annotated_dc_annotated(method_definition):
    """Test is annotated dc annotated."""

    @dataclass
    class TestAnnotatedDataClass:
        """Test annotated data class."""

        value: int

    annotated_dataclass = Annotated[TestAnnotatedDataClass, "test_annotation"]
    result = method_definition.is_annotated_dc(annotation=annotated_dataclass)
    assert result


def test_reorder_params(method_definition):
    """Test reorder params."""
    params = {
        "provider": Parameter.empty,
        "extra_params": Parameter.empty,
        "param1": Parameter.empty,
        "param2": Parameter.empty,
    }
    result = method_definition.reorder_params(params=params)
    assert result
    assert list(result.keys()) == ["param1", "param2", "provider", "extra_params"]


def test_build_func_params(method_definition):
    """Test build func params."""
    param_map = {
        "param1": Parameter(
            name="param1", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=type(None)
        ),
        "param2": Parameter(
            "param2", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=int
        ),
        "param3": Parameter(
            "param3",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=pandas.core.frame.DataFrame,
        ),
    }

    expected_output = (
        "param1: None,\n        param2: int,\n        param3: pandas.DataFrame"
    )
    output = method_definition.build_func_params(param_map)

    assert output == expected_output


@pytest.mark.parametrize(
    "return_type, expected_output",
    [
        (_empty, "None"),
        (int, "int"),
    ],
)
def test_build_func_returns(method_definition, return_type, expected_output):
    """Test build func returns."""
    output = method_definition.build_func_returns(return_type=return_type)
    assert output == expected_output


def test_build_command_method_signature(method_definition):
    """Test build command method signature."""
    formatted_params = {
        "param1": Parameter("NoneType", kind=Parameter.POSITIONAL_OR_KEYWORD),
        "param2": Parameter("int", kind=Parameter.POSITIONAL_OR_KEYWORD),
    }
    return_type = int
    output = method_definition.build_command_method_signature(
        func_name="test_func",
        formatted_params=formatted_params,
        return_type=return_type,
    )
    assert output


def test_build_command_method_doc(method_definition):
    """Test build command method doc."""

    def some_func():
        """Do some func doc."""

    formatted_params = {
        "param1": Parameter("NoneType", kind=Parameter.POSITIONAL_OR_KEYWORD),
        "param2": Parameter("int", kind=Parameter.POSITIONAL_OR_KEYWORD),
    }

    output = method_definition.build_command_method_doc(
        func=some_func, formatted_params=formatted_params
    )
    assert output
    assert isinstance(output, str)


def test_build_command_method_body(method_definition):
    """Test build command method body."""

    def some_func():
        """Do some func doc."""
        return 42

    with patch(
        "openbb_core.app.static.package_builder.MethodDefinition.is_data_processing_function",
        **{"return_value": False},
    ):
        output = method_definition.build_command_method_body(
            path="openbb_core.app.static.container.Container", func=some_func
        )

    assert output
    assert isinstance(output, str)


def test_build_command_method(method_definition):
    """Test build command method."""

    def some_func():
        """Do some func doc."""
        return 42

    with patch(
        "openbb_core.app.static.package_builder.MethodDefinition.is_data_processing_function",
        **{"return_value": False},
    ):
        output = method_definition.build_command_method(
            path="openbb_core.app.static.container.Container",
            func=some_func,
            model_name=None,
        )

    assert output
    assert isinstance(output, str)


@pytest.fixture(scope="module")
def import_definition():
    """Return import definition."""
    return ImportDefinition()


def test_import_definition_init(import_definition):
    """Test import definition init."""
    assert import_definition


def test_filter_hint_type_list(import_definition):
    """Test filter type hint list."""
    output = import_definition.filter_hint_type_list(
        hint_type_list=[int, str, float, bool, _empty, _empty, _empty, _empty]
    )
    assert output == []


def test_import_definition_get_path_hint_type_list(import_definition):
    """Test import definition get path hint type list."""
    hint_type_list = import_definition.get_path_hint_type_list(
        path="openbb_core.app.static.container.Container"
    )
    assert hint_type_list == []


def test_import_definition_build(import_definition):
    """Test import definition build."""
    code = import_definition.build(path="openbb_core.app.static.container.Container")
    assert code


@pytest.fixture(scope="module")
def path_handler():
    """Return path handler."""
    return PathHandler()


def test_path_handler_init(path_handler):
    """Test path handler init."""
    assert path_handler


@pytest.fixture(scope="module")
def route_map(path_handler):
    """Return route map."""
    return path_handler.build_route_map()


def test_build_route_map(route_map):
    """Test build route map."""
    assert route_map
    assert isinstance(route_map, dict)


@pytest.fixture(scope="module")
def path_list(path_handler, route_map):
    """Return path list."""
    return path_handler.build_path_list(route_map=route_map)


def test_build_path_list(path_list):
    """Test build path list."""
    assert path_list
    assert isinstance(path_list, list)


def test_get_route(path_handler, route_map):
    """Test get route."""
    route = path_handler.get_route(route_map=route_map, path="/equity/price/historical")

    assert route


def test_get_child_path_list(path_handler, path_list):
    """Test get child path list."""
    child_path_list = path_handler.get_child_path_list(
        path="/equity", path_list=path_list
    )

    assert child_path_list
    assert isinstance(child_path_list, list)


def test_clean_path(path_handler):
    """Test clean path."""
    path = "/equity/price/historical"
    result = path_handler.clean_path(path=path)
    assert result == "equity_price_historical"


def test_build_module_name(path_handler):
    """Test build module name."""
    module_name = path_handler.build_module_name(path="")
    assert module_name == "__extensions__"

    module_name = path_handler.build_module_name(path="/equity/price/historical")
    assert module_name == "equity_price_historical"


def test_build_module_class(path_handler):
    """Test build module class."""
    module_class = path_handler.build_module_class(path="")
    assert module_class == "Extensions"

    module_class = path_handler.build_module_class(path="/equity/price/historical")
    assert module_class == "ROUTER_equity_price_historical"


@pytest.fixture(scope="module")
def docstring_generator():
    """Return package builder."""
    return DocstringGenerator()


def test_docstring_generator_init(docstring_generator):
    """Test docstring generator init."""
    assert docstring_generator


def test_get_OBBject_description(docstring_generator):
    """Test build docstring."""
    docstring = docstring_generator.get_OBBject_description(
        "SomeModel", "some_provider"
    )
    assert docstring


def test_generate_model_docstring(docstring_generator):
    """Test generate model docstring."""
    docstring = ""
    model_name = "WorldNews"
    summary = "This is a summary."

    pi = docstring_generator.provider_interface
    params = pi.params[model_name]
    return_schema = pi.return_schema[model_name]
    returns = return_schema.model_fields

    formatted_params = {
        "param1": Parameter("NoneType", kind=Parameter.POSITIONAL_OR_KEYWORD),
        "param2": Parameter("int", kind=Parameter.POSITIONAL_OR_KEYWORD),
    }
    explicit_dict = dict(formatted_params)

    docstring = docstring_generator.generate_model_docstring(
        model_name=model_name,
        summary=summary,
        explicit_params=explicit_dict,
        params=params,
        returns=returns,
        results_type="List[WorldNews]",
    )

    assert docstring
    assert summary in docstring
    assert "Parameters" in docstring
    assert "Returns" in docstring
    assert "WorldNews" in docstring


def test_generate(docstring_generator):
    """Test generate docstring."""

    def some_func():
        """Some func docstring."""

    formatted_params = {
        "param1": Parameter("NoneType", kind=Parameter.POSITIONAL_OR_KEYWORD),
        "param2": Parameter("int", kind=Parameter.POSITIONAL_OR_KEYWORD),
    }

    doc = docstring_generator.generate(
        func=some_func, formatted_params=formatted_params, model_name="WorldNews"
    )
    assert doc
    assert "Parameters" in doc
    assert "Returns" in doc


def test_read_extension_map(package_builder, tmp_package_dir):
    """Test read extension map."""

    PATH = "openbb_core.app.static.package_builder."
    open_mock = mock_open()
    with patch(PATH + "open", open_mock), patch(PATH + "load") as mock_load:
        package_builder._read_extension_map(tmp_package_dir)
        open_mock.assert_called_once_with(Path(tmp_package_dir, "extension_map.json"))
        mock_load.assert_called_once()


@pytest.mark.parametrize(
    "ext_built, ext_installed, ext_inst_version, expected_add, expected_remove",
    [
        (
            {
                "openbb_core_extension": [
                    "ext_1@0.0.0",
                    "ext_2@0.0.0",
                ],
                "openbb_provider_extension": [
                    "prov_1@0.0.0",
                    "prov_2@1.1.1",
                ],
            },
            EntryPoints(
                (
                    EntryPoint(
                        name="ext_2", value="...", group="openbb_core_extension"
                    ),
                    EntryPoint(
                        name="prov_2", value="...", group="openbb_provider_extension"
                    ),
                )
            ),
            "0.0.0",
            {"prov_2@0.0.0"},
            {"ext_1@0.0.0", "prov_1@0.0.0", "prov_2@1.1.1"},
        ),
        (
            {
                "openbb_core_extension": ["ext_1@9.9.9"],
                "openbb_provider_extension": ["prov_2@0.0.0"],
            },
            EntryPoints(
                (
                    EntryPoint(
                        name="ext_2", value="...", group="openbb_core_extension"
                    ),
                    EntryPoint(
                        name="prov_1", value="...", group="openbb_provider_extension"
                    ),
                )
            ),
            "5.5.5",
            {"ext_2@5.5.5", "prov_1@5.5.5"},
            {"ext_1@9.9.9", "prov_2@0.0.0"},
        ),
    ],
)
def test_package_diff(
    package_builder,
    tmp_package_dir,
    ext_built,
    ext_installed,
    ext_inst_version,
    expected_add,
    expected_remove,
):
    """Test package differences."""

    def mock_entry_points(group):
        return ext_installed.select(**{"group": group})

    PATH = "openbb_core.app.static.package_builder."
    with patch.object(
        PackageBuilder, "_read_extension_map"
    ) as mock_read_extension_map, patch(
        PATH + "entry_points", mock_entry_points
    ), patch.object(
        EntryPoint, "dist", new_callable=PropertyMock
    ) as mock_obj:

        class MockPathDistribution:
            version = ext_inst_version

        mock_obj.return_value = MockPathDistribution()
        mock_read_extension_map.return_value = ext_built

        add, remove = package_builder._diff(tmp_package_dir)

        # We add whatever is not built, but is installed
        assert add == expected_add
        # We remove whatever is built, but is not installed
        assert remove == expected_remove


@pytest.mark.parametrize(
    "add, remove, openbb_auto_build",
    [
        (set(), set(), True),
        ({"this"}, set(), True),
        (set(), {"that"}, True),
        ({"this"}, {"that"}, True),
        ({"this"}, {"that"}, False),
    ],
)
def test_auto_build(package_builder, tmp_package_dir, add, remove, openbb_auto_build):
    """Test auto build."""

    with patch.object(PackageBuilder, "_diff") as mock_package_diff, patch.object(
        PackageBuilder, "build"
    ) as mock_build, patch.object(Env, "AUTO_BUILD", openbb_auto_build):
        mock_package_diff.return_value = add, remove

        package_builder.auto_build()

    if openbb_auto_build:
        mock_package_diff.assert_called_once_with(Path(tmp_package_dir, "package"))
        if add or remove:
            mock_build.assert_called_once()
    else:
        mock_package_diff.assert_not_called()
        mock_build.assert_not_called()
