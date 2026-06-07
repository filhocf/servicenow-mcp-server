"""Tests for tool registry and handlers."""

from unittest.mock import AsyncMock

import pytest

from servicenow_mcp.config import FeaturesConfig
from servicenow_mcp.tools import ToolRegistry


class TestToolRegistry:
    """Test tool registry functionality."""

    def test_tool_registration(self):
        """Test that all tools are registered correctly."""
        features = FeaturesConfig()  # All features enabled by default
        registry = ToolRegistry(features)

        # Check that tools are registered
        tools = registry.get_enabled_tools()
        tool_names = [tool.name for tool in tools]

        # Check core tools
        assert "query_table" in tool_names
        assert "get_record" in tool_names
        assert "create_record" in tool_names
        assert "update_record" in tool_names
        assert "delete_record" in tool_names

        # Check feature-specific tools
        assert "incident_create" in tool_names
        assert "incident_update" in tool_names
        assert "incident_search" in tool_names
        assert "change_create" in tool_names
        assert "ci_search" in tool_names
        assert "ci_relationships" in tool_names
        assert "user_search" in tool_names
        assert "kb_search" in tool_names
        assert "catalog_items" in tool_names
        assert "get_stats" in tool_names

    def test_feature_disabling(self):
        """Test that disabling features removes corresponding tools."""
        features = FeaturesConfig(
            incident_management=False,
            change_management=False,
            cmdb=False,
            custom_tables=False,
        )
        registry = ToolRegistry(features)

        tools = registry.get_enabled_tools()
        tool_names = [tool.name for tool in tools]

        # Incident tools should be disabled
        assert "incident_create" not in tool_names
        assert "incident_update" not in tool_names
        assert "incident_search" not in tool_names

        # Change tools should be disabled
        assert "change_create" not in tool_names

        # CMDB tools should be disabled
        assert "ci_search" not in tool_names
        assert "ci_relationships" not in tool_names

        # Custom table tools should be disabled
        assert "query_table" not in tool_names
        assert "get_record" not in tool_names
        assert "create_record" not in tool_names
        assert "update_record" not in tool_names
        assert "delete_record" not in tool_names

        # Other tools should still be enabled
        assert "user_search" in tool_names
        assert "kb_search" in tool_names
        assert "catalog_items" in tool_names

    def test_get_handler(self):
        """Test getting handlers for tools."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Test getting valid handler
        handler = registry.get_handler("incident_create")
        assert handler is not None
        assert callable(handler)

        # Test getting invalid handler
        handler = registry.get_handler("non_existent_tool")
        assert handler is None

    @pytest.mark.asyncio
    async def test_incident_create_handler(self):
        """Test incident creation handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Mock client
        mock_client = AsyncMock()
        mock_client.create_incident.return_value = {
            "sys_id": "123",
            "number": "INC0000001",
        }

        handler = registry.get_handler("incident_create")
        result = await handler(
            mock_client,
            {
                "short_description": "Test incident",
                "urgency": 1,
                "impact": 1,
                "assignment_group": "IT Support",
            },
        )

        assert result["sys_id"] == "123"
        assert result["number"] == "INC0000001"

        # Verify client was called correctly
        mock_client.create_incident.assert_called_once()
        call_args = mock_client.create_incident.call_args[0][0]
        assert call_args["short_description"] == "Test incident"
        assert call_args["urgency"] == 1
        assert call_args["impact"] == 1
        assert call_args["assignment_group"] == "IT Support"

    @pytest.mark.asyncio
    async def test_incident_update_handler(self):
        """Test incident update handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Mock client
        mock_client = AsyncMock()
        mock_client.query_incidents.return_value = [
            {"sys_id": "123", "number": "INC0000001"}
        ]
        mock_client.update_incident.return_value = {
            "sys_id": "123",
            "number": "INC0000001",
            "state": "2",
        }

        handler = registry.get_handler("incident_update")
        result = await handler(
            mock_client,
            {"number": "INC0000001", "state": 2, "work_notes": "Working on this"},
        )

        assert result["state"] == "2"

        # Verify client calls
        mock_client.query_incidents.assert_called_once_with(
            query="number=INC0000001", limit=1
        )
        mock_client.update_incident.assert_called_once_with(
            "123", {"state": 2, "work_notes": "Working on this"}, display_value="both"
        )

    @pytest.mark.asyncio
    async def test_incident_update_not_found(self):
        """Test incident update when incident not found."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Mock client
        mock_client = AsyncMock()
        mock_client.query_incidents.return_value = []

        handler = registry.get_handler("incident_update")
        result = await handler(mock_client, {"number": "INC9999999", "state": 2})

        assert result["error"] == "Incident INC9999999 not found"

    @pytest.mark.asyncio
    async def test_query_table_handler(self):
        """Test query table handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Mock client
        mock_client = AsyncMock()
        mock_client.query_records.return_value = [
            {"sys_id": "1", "name": "Item 1"},
            {"sys_id": "2", "name": "Item 2"},
        ]

        handler = registry.get_handler("query_table")
        result = await handler(
            mock_client,
            {
                "table": "sc_cat_item",
                "query": "active=true",
                "fields": ["name", "price"],
                "limit": 50,
                "order_by": "-sys_created_on",
            },
        )

        assert len(result) == 2
        assert result[0]["name"] == "Item 1"

        # Verify client call
        mock_client.query_records.assert_called_once_with(
            table="sc_cat_item",
            query="active=true",
            fields=["name", "price"],
            limit=50,
            offset=0,
            order_by="-sys_created_on",
            display_value="both",
        )

    @pytest.mark.asyncio
    async def test_ci_search_handler(self):
        """Test CI search handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Mock client
        mock_client = AsyncMock()
        mock_client.query_records.return_value = [
            {"sys_id": "ci1", "name": "PROD-WEB-01"},
            {"sys_id": "ci2", "name": "PROD-DB-01"},
        ]

        handler = registry.get_handler("ci_search")
        result = await handler(
            mock_client,
            {
                "name": "PROD*",
                "class": "cmdb_ci_server",
                "operational_status": 1,
                "environment": "production",
            },
        )

        assert len(result) == 2

        # Verify query construction
        mock_client.query_records.assert_called_once()
        call_args = mock_client.query_records.call_args
        assert call_args[0][0] == "cmdb_ci"
        query = call_args[1]["query"]
        assert "nameLIKEPROD*" in query
        assert "sys_class_name=cmdb_ci_server" in query
        assert "operational_status=1" in query
        assert "u_environment=production" in query

    @pytest.mark.asyncio
    async def test_user_search_handler(self):
        """Test user search handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Mock client
        mock_client = AsyncMock()
        mock_client.query_users.return_value = [
            {
                "sys_id": "user1",
                "user_name": "john.doe",
                "email": "john.doe@example.com",
            }
        ]

        handler = registry.get_handler("user_search")
        result = await handler(
            mock_client, {"name": "John", "active": True, "department": "IT"}
        )

        assert len(result) == 1
        assert result[0]["user_name"] == "john.doe"

        # Verify query construction
        mock_client.query_users.assert_called_once()
        call_args = mock_client.query_users.call_args
        query = call_args[1]["query"]
        assert "first_nameLIKEJohn" in query
        assert "active=true" in query
        assert "department.name=IT" in query

    @pytest.mark.asyncio
    async def test_get_stats_handler(self):
        """Test aggregate statistics handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        # Mock client
        mock_client = AsyncMock()
        mock_client.get_aggregate.return_value = [
            {"priority": 1, "count": 15},
            {"priority": 2, "count": 30},
            {"priority": 3, "count": 45},
        ]

        handler = registry.get_handler("get_stats")
        result = await handler(
            mock_client,
            {
                "table": "incident",
                "group_by": ["priority"],
                "aggregates": [{"type": "COUNT", "field": "sys_id", "alias": "count"}],
                "query": "active=true",
            },
        )

        assert len(result) == 3
        assert result[0]["count"] == 15

        # Verify client call
        mock_client.get_aggregate.assert_called_once_with(
            table="incident",
            query="active=true",
            group_by=["priority"],
            aggregate=[{"type": "COUNT", "field": "sys_id", "alias": "count"}],
        )

    @pytest.mark.asyncio
    async def test_change_create_custom_fields(self):
        """Test change_create with custom_fields."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        mock_client = AsyncMock()
        mock_client.create_record.return_value = {
            "sys_id": "chg123",
            "number": "CHG0000001",
        }

        handler = registry.get_handler("change_create")
        result = await handler(
            mock_client,
            {
                "short_description": "Deploy v2",
                "type": "normal",
                "custom_fields": {"u_environment": "production", "u_team": "platform"},
            },
        )

        assert result["number"] == "CHG0000001"
        call_args = mock_client.create_record.call_args
        data = call_args[0][1]
        assert data["u_environment"] == "production"
        assert data["u_team"] == "platform"

    @pytest.mark.asyncio
    async def test_ritm_search_handler(self):
        """Test ritm_search handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        mock_client = AsyncMock()
        mock_client.query_records.return_value = [
            {"sys_id": "ritm1", "number": "RITM0000001"}
        ]

        handler = registry.get_handler("ritm_search")
        result = await handler(
            mock_client,
            {"state": "1", "requested_for": "john.doe", "limit": 10},
        )

        assert len(result) == 1
        mock_client.query_records.assert_called_once()
        call_args = mock_client.query_records.call_args
        assert call_args[0][0] == "sc_req_item"
        assert "state=1" in call_args[1]["query"]
        assert "requested_for.user_name=john.doe" in call_args[1]["query"]

    @pytest.mark.asyncio
    async def test_ritm_create_handler(self):
        """Test ritm_create handler."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)

        mock_client = AsyncMock()
        mock_client.order_catalog_item.return_value = {
            "sys_id": "ritm2",
            "number": "RITM0000002",
        }

        handler = registry.get_handler("ritm_create")
        await handler(
            mock_client,
            {
                "cat_item": "cat_sys_id_123",
                "variables": {"urgency": "high"},
                "requested_for": "user_sys_id",
            },
        )

        mock_client.order_catalog_item.assert_called_once_with(
            cat_item="cat_sys_id_123",
            variables={"urgency": "high"},
            requested_for="user_sys_id",
        )

    def test_ritm_tools_registered(self):
        """Test that RITM tools are registered."""
        features = FeaturesConfig()
        registry = ToolRegistry(features)
        tool_names = [t.name for t in registry.get_enabled_tools()]
        assert "ritm_search" in tool_names
        assert "ritm_create" in tool_names
