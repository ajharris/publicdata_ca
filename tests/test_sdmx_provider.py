"""Tests for the SDMX provider."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from publicdata_ca.provider import Provider, DatasetRef
from publicdata_ca.providers.sdmx import (
    get_sdmx_dataflow,
    get_sdmx_data_structure,
    fetch_sdmx_data,
    download_sdmx_data,
    SDMXProvider,
)


# Sample SDMX XML responses for testing

SAMPLE_DATAFLOW_XML = """<?xml version="1.0" encoding="UTF-8"?>
<message:Structure xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
                   xmlns:structure="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
                   xmlns:common="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
    <message:Structures>
        <structure:Dataflows>
            <structure:Dataflow id="QNA" agencyID="OECD" version="1.0">
                <common:Name xml:lang="en">Quarterly National Accounts</common:Name>
                <common:Description xml:lang="en">National accounts data</common:Description>
                <structure:Structure>
                    <Ref agencyID="OECD" id="QNA_DSD" version="1.0"/>
                </structure:Structure>
            </structure:Dataflow>
        </structure:Dataflows>
    </message:Structures>
</message:Structure>
"""

SAMPLE_DSD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<message:Structure xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
                   xmlns:structure="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
                   xmlns:common="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
    <message:Structures>
        <structure:DataStructures>
            <structure:DataStructure id="QNA_DSD" agencyID="OECD" version="1.0">
                <common:Name xml:lang="en">QNA Data Structure</common:Name>
                <structure:DataStructureComponents>
                    <structure:DimensionList>
                        <structure:Dimension id="LOCATION">
                            <common:Name xml:lang="en">Location</common:Name>
                        </structure:Dimension>
                        <structure:Dimension id="SUBJECT">
                            <common:Name xml:lang="en">Subject</common:Name>
                        </structure:Dimension>
                        <structure:TimeDimension id="TIME_PERIOD">
                            <common:Name xml:lang="en">Time Period</common:Name>
                        </structure:TimeDimension>
                    </structure:DimensionList>
                    <structure:AttributeList>
                        <structure:Attribute id="UNIT">
                            <common:Name xml:lang="en">Unit</common:Name>
                        </structure:Attribute>
                    </structure:AttributeList>
                    <structure:MeasureList>
                        <structure:PrimaryMeasure id="OBS_VALUE">
                            <common:Name xml:lang="en">Observation Value</common:Name>
                        </structure:PrimaryMeasure>
                    </structure:MeasureList>
                </structure:DataStructureComponents>
            </structure:DataStructure>
        </structure:DataStructures>
    </message:Structures>
</message:Structure>
"""

SAMPLE_SDMX_DATA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<message:GenericData xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
                     xmlns:generic="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic">
    <message:DataSet>
        <generic:Series>
            <generic:SeriesKey>
                <generic:Value id="LOCATION" value="AUS"/>
                <generic:Value id="SUBJECT" value="GDP"/>
            </generic:SeriesKey>
            <generic:Obs>
                <generic:ObsDimension value="2020-Q1"/>
                <generic:ObsValue value="1000"/>
            </generic:Obs>
        </generic:Series>
    </message:DataSet>
</message:GenericData>
"""

SAMPLE_SDMX_JSON = {
    "data": {
        "dataSets": [
            {
                "series": {
                    "0:0": {
                        "observations": {
                            "0": [1000]
                        }
                    }
                }
            }
        ]
    }
}


class TestGetSdmxDataflow:
    """Tests for get_sdmx_dataflow function."""
    
    def test_get_dataflow_success(self):
        """Test successfully retrieving dataflow metadata."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_DATAFLOW_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            metadata = get_sdmx_dataflow(
                'https://sdmx.example.org/rest',
                'OECD',
                'QNA'
            )
            
            assert metadata['id'] == 'QNA'
            assert metadata['agency_id'] == 'OECD'
            assert 'en' in metadata['name']
            assert metadata['name']['en'] == 'Quarterly National Accounts'
            assert 'en' in metadata['description']
            assert 'structure_ref' in metadata
            assert metadata['structure_ref']['id'] == 'QNA_DSD'
    
    def test_get_dataflow_with_version(self):
        """Test retrieving dataflow with specific version."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_DATAFLOW_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response) as mock_req:
            metadata = get_sdmx_dataflow(
                'https://sdmx.example.org/rest',
                'OECD',
                'QNA',
                version='2.0'
            )
            
            # Verify the URL includes the version
            called_url = mock_req.call_args[0][0]
            assert 'dataflow/OECD/QNA/2.0' in called_url
            assert metadata['version'] == '2.0'
    
    def test_get_dataflow_network_error(self):
        """Test handling of network errors."""
        with patch('publicdata_ca.providers.sdmx.retry_request', side_effect=Exception("Network error")):
            with pytest.raises(RuntimeError, match="Failed to get SDMX dataflow"):
                get_sdmx_dataflow(
                    'https://sdmx.example.org/rest',
                    'OECD',
                    'QNA'
                )
    
    def test_get_dataflow_invalid_xml(self):
        """Test handling of invalid XML response."""
        mock_response = Mock()
        mock_response.read.return_value = b"<invalid>XML"
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            with pytest.raises(RuntimeError, match="Failed to parse SDMX XML"):
                get_sdmx_dataflow(
                    'https://sdmx.example.org/rest',
                    'OECD',
                    'QNA'
                )
    
    def test_get_dataflow_no_dataflow_element(self):
        """Test handling of response without dataflow element."""
        mock_response = Mock()
        mock_response.read.return_value = b"<root></root>"
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            with pytest.raises(RuntimeError, match="No dataflow found"):
                get_sdmx_dataflow(
                    'https://sdmx.example.org/rest',
                    'OECD',
                    'QNA'
                )


class TestGetSdmxDataStructure:
    """Tests for get_sdmx_data_structure function."""
    
    def test_get_data_structure_success(self):
        """Test successfully retrieving data structure definition."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_DSD_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            metadata = get_sdmx_data_structure(
                'https://sdmx.example.org/rest',
                'OECD',
                'QNA_DSD'
            )
            
            assert metadata['id'] == 'QNA_DSD'
            assert metadata['agency_id'] == 'OECD'
            assert 'en' in metadata['name']
            assert len(metadata['dimensions']) == 3
            assert len(metadata['attributes']) == 1
            assert len(metadata['measures']) == 1
            
            # Check dimension details
            location_dim = next(d for d in metadata['dimensions'] if d['id'] == 'LOCATION')
            assert 'name' in location_dim
            assert location_dim['name']['en'] == 'Location'
            
            # Check attribute details
            assert metadata['attributes'][0]['id'] == 'UNIT'
            
            # Check measure details
            assert metadata['measures'][0]['id'] == 'OBS_VALUE'
    
    def test_get_data_structure_with_version(self):
        """Test retrieving data structure with specific version."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_DSD_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response) as mock_req:
            metadata = get_sdmx_data_structure(
                'https://sdmx.example.org/rest',
                'OECD',
                'QNA_DSD',
                version='2.0'
            )
            
            # Verify the URL includes the version
            called_url = mock_req.call_args[0][0]
            assert 'datastructure/OECD/QNA_DSD/2.0' in called_url
            assert metadata['version'] == '2.0'
    
    def test_get_data_structure_network_error(self):
        """Test handling of network errors."""
        with patch('publicdata_ca.providers.sdmx.retry_request', side_effect=Exception("Network error")):
            with pytest.raises(RuntimeError, match="Failed to get SDMX data structure"):
                get_sdmx_data_structure(
                    'https://sdmx.example.org/rest',
                    'OECD',
                    'QNA_DSD'
                )


class TestFetchSdmxData:
    """Tests for fetch_sdmx_data function."""
    
    def test_fetch_data_xml_format(self):
        """Test fetching data in SDMX-ML (XML) format."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_SDMX_DATA_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            result = fetch_sdmx_data(
                'https://sdmx.example.org/rest',
                'OECD,QNA,1.0',
                key='AUS...',
                format='sdmx-ml'
            )
            
            assert result['format'] == 'sdmx-ml'
            assert result['dataflow'] == 'OECD,QNA,1.0'
            assert 'raw_data' in result
            assert isinstance(result['raw_data'], str)
            assert 'GenericData' in result['raw_data']
    
    def test_fetch_data_json_format(self):
        """Test fetching data in SDMX-JSON format."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(SAMPLE_SDMX_JSON).encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            result = fetch_sdmx_data(
                'https://sdmx.example.org/rest',
                'OECD,QNA,1.0',
                key='AUS...',
                format='sdmx-json'
            )
            
            assert result['format'] == 'sdmx-json'
            assert isinstance(result['raw_data'], dict)
            assert 'data' in result['raw_data']
    
    def test_fetch_data_with_time_filter(self):
        """Test fetching data with start and end period filters."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_SDMX_DATA_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response) as mock_req:
            result = fetch_sdmx_data(
                'https://sdmx.example.org/rest',
                'OECD,QNA,1.0',
                key='AUS...',
                start_period='2020-Q1',
                end_period='2023-Q4'
            )
            
            # Verify URL contains time filters
            called_url = mock_req.call_args[0][0]
            assert 'startPeriod=2020-Q1' in called_url
            assert 'endPeriod=2023-Q4' in called_url
    
    def test_fetch_data_simple_dataflow_id(self):
        """Test fetching data with simple dataflow ID (no agency/version)."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_SDMX_DATA_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response) as mock_req:
            result = fetch_sdmx_data(
                'https://sdmx.example.org/rest',
                'QNA',
                provider_ref='OECD'
            )
            
            # Verify URL construction
            called_url = mock_req.call_args[0][0]
            assert 'data/OECD/QNA' in called_url
    
    def test_fetch_data_with_additional_params(self):
        """Test fetching data with additional SDMX parameters."""
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_SDMX_DATA_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response) as mock_req:
            result = fetch_sdmx_data(
                'https://sdmx.example.org/rest',
                'OECD,QNA,1.0',
                dimensionAtObservation='AllDimensions',
                detail='Full'
            )
            
            # Verify URL contains additional parameters
            called_url = mock_req.call_args[0][0]
            assert 'dimensionAtObservation=AllDimensions' in called_url
            assert 'detail=Full' in called_url


class TestDownloadSdmxData:
    """Tests for download_sdmx_data function."""
    
    def test_download_data_success(self, tmp_path):
        """Test successfully downloading SDMX data to file."""
        output_file = tmp_path / "test_data.xml"
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(output_file)
            
            result = download_sdmx_data(
                'https://sdmx.example.org/rest',
                'OECD,QNA,1.0',
                str(output_file),
                key='AUS...'
            )
            
            assert result['file'] == str(output_file)
            assert result['format'] == 'sdmx-ml'
            assert result['dataflow'] == 'OECD,QNA,1.0'
            assert 'url' in result
            
            # Verify download_file was called
            mock_download.assert_called_once()
            call_args = mock_download.call_args
            assert 'data/OECD/QNA/1.0/AUS...' in call_args[0][0]
    
    def test_download_data_json_format(self, tmp_path):
        """Test downloading data in JSON format."""
        output_file = tmp_path / "test_data.json"
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(output_file)
            
            result = download_sdmx_data(
                'https://sdmx.example.org/rest',
                'OECD,QNA,1.0',
                str(output_file),
                format='sdmx-json'
            )
            
            # Verify format parameter in URL
            call_args = mock_download.call_args
            assert 'format=sdmx-json' in call_args[0][0]
            assert result['format'] == 'sdmx-json'
    
    def test_download_data_creates_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "new_dir"
        output_file = output_dir / "data.xml"
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(output_file)
            
            result = download_sdmx_data(
                'https://sdmx.example.org/rest',
                'QNA',
                str(output_file)
            )
            
            assert output_dir.exists()
    
    def test_download_data_with_retries(self, tmp_path):
        """Test download with custom retry count."""
        output_file = tmp_path / "test_data.xml"
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(output_file)
            
            result = download_sdmx_data(
                'https://sdmx.example.org/rest',
                'QNA',
                str(output_file),
                max_retries=5
            )
            
            # Verify max_retries parameter
            call_kwargs = mock_download.call_args[1]
            assert call_kwargs['max_retries'] == 5


class TestSDMXProvider:
    """Tests for SDMXProvider class."""
    
    def test_provider_creation(self):
        """Test creating an SDMX provider instance."""
        provider = SDMXProvider(
            name='oecd',
            base_url='https://sdmx.oecd.org/public/rest'
        )
        
        assert provider.name == 'oecd'
        assert provider.base_url == 'https://sdmx.oecd.org/public/rest'
        assert isinstance(provider, Provider)
    
    def test_provider_default_name(self):
        """Test provider uses default name if not specified."""
        provider = SDMXProvider()
        assert provider.name == 'sdmx'
    
    def test_search_not_implemented(self):
        """Test that search raises NotImplementedError."""
        provider = SDMXProvider(base_url='https://sdmx.example.org')
        
        with pytest.raises(NotImplementedError, match="Search is not implemented"):
            provider.search('gdp')
    
    def test_resolve_with_full_dataflow_id(self):
        """Test resolving with full dataflow ID (AGENCY,DATAFLOW,VERSION)."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_DATAFLOW_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            ref = DatasetRef(
                provider='oecd',
                id='OECD,QNA,1.0',
                params={}
            )
            
            metadata = provider.resolve(ref)
            
            assert metadata['dataflow_id'] == 'OECD,QNA,1.0'
            assert 'dataflow_metadata' in metadata
            assert metadata['provider'] == 'sdmx'
    
    def test_resolve_with_simple_dataflow_id(self):
        """Test resolving with simple dataflow ID."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        mock_response = Mock()
        mock_response.read.return_value = SAMPLE_DATAFLOW_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', return_value=mock_response):
            ref = DatasetRef(
                provider='sdmx',
                id='QNA',
                params={'agency_id': 'OECD'}
            )
            
            metadata = provider.resolve(ref)
            
            assert metadata['dataflow_id'] == 'QNA'
            assert 'dataflow_metadata' in metadata
    
    def test_resolve_with_dsd_metadata(self):
        """Test resolving with data structure definition metadata."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        mock_dataflow = Mock()
        mock_dataflow.read.return_value = SAMPLE_DATAFLOW_XML.encode('utf-8')
        
        mock_dsd = Mock()
        mock_dsd.read.return_value = SAMPLE_DSD_XML.encode('utf-8')
        
        with patch('publicdata_ca.providers.sdmx.retry_request', side_effect=[mock_dataflow, mock_dsd]):
            ref = DatasetRef(
                provider='sdmx',
                id='OECD,QNA,1.0',
                params={'include_dsd': True}
            )
            
            metadata = provider.resolve(ref)
            
            assert 'dsd_metadata' in metadata
            assert len(metadata['dsd_metadata']['dimensions']) == 3
    
    def test_resolve_no_base_url(self):
        """Test resolve raises error when base_url is not configured."""
        provider = SDMXProvider()
        
        ref = DatasetRef(
            provider='sdmx',
            id='QNA',
            params={}
        )
        
        with pytest.raises(ValueError, match="base_url must be provided"):
            provider.resolve(ref)
    
    def test_fetch_with_filters(self, tmp_path):
        """Test fetching data with dimension filters and time range."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(tmp_path / "data.xml")
            
            ref = DatasetRef(
                provider='sdmx',
                id='OECD,QNA,1.0',
                params={
                    'key': 'AUS...',
                    'start_period': '2020-Q1',
                    'end_period': '2023-Q4',
                }
            )
            
            result = provider.fetch(ref, str(tmp_path))
            
            assert result['provider'] == 'sdmx'
            assert len(result['files']) == 1
            assert result['dataflow'] == 'OECD,QNA,1.0'
            
            # Verify download was called with correct URL
            call_args = mock_download.call_args
            assert 'startPeriod=2020-Q1' in call_args[0][0]
            assert 'endPeriod=2023-Q4' in call_args[0][0]
    
    def test_fetch_json_format(self, tmp_path):
        """Test fetching data in JSON format."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(tmp_path / "data.json")
            
            ref = DatasetRef(
                provider='sdmx',
                id='QNA',
                params={
                    'format': 'sdmx-json',
                }
            )
            
            result = provider.fetch(ref, str(tmp_path))
            
            assert result['format'] == 'sdmx-json'
            # Verify filename has .json extension
            assert result['files'][0].endswith('.json')
    
    def test_fetch_custom_filename(self, tmp_path):
        """Test fetching with custom filename."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(tmp_path / "custom.xml")
            
            ref = DatasetRef(
                provider='sdmx',
                id='QNA',
                params={}
            )
            
            result = provider.fetch(ref, str(tmp_path), filename='custom.xml')
            
            # Verify custom filename was used
            call_args = mock_download.call_args
            assert 'custom.xml' in call_args[0][1]
    
    def test_fetch_sanitizes_dataflow_id(self, tmp_path):
        """Test that dataflow ID is sanitized for filename."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(tmp_path / "OECD_QNA_1.0.xml")
            
            ref = DatasetRef(
                provider='sdmx',
                id='OECD,QNA,1.0',
                params={}
            )
            
            result = provider.fetch(ref, str(tmp_path))
            
            # Verify dataflow ID is sanitized (commas replaced with underscores)
            assert 'OECD_QNA_1.0' in result['dataset_id']
    
    def test_fetch_with_additional_params(self, tmp_path):
        """Test fetching with additional SDMX parameters."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(tmp_path / "data.xml")
            
            ref = DatasetRef(
                provider='sdmx',
                id='QNA',
                params={
                    'dimensionAtObservation': 'AllDimensions',
                    'detail': 'Full',
                }
            )
            
            result = provider.fetch(ref, str(tmp_path))
            
            # Verify additional parameters in URL
            call_args = mock_download.call_args
            assert 'dimensionAtObservation=AllDimensions' in call_args[0][0]
            assert 'detail=Full' in call_args[0][0]
    
    def test_fetch_no_base_url(self, tmp_path):
        """Test fetch raises error when base_url is not configured."""
        provider = SDMXProvider()
        
        ref = DatasetRef(
            provider='sdmx',
            id='QNA',
            params={}
        )
        
        with pytest.raises(ValueError, match="base_url must be provided"):
            provider.fetch(ref, str(tmp_path))
    
    def test_fetch_uses_provider_base_url(self, tmp_path):
        """Test that fetch uses provider's base_url when not in params."""
        provider = SDMXProvider(base_url='https://sdmx.example.org/rest')
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(tmp_path / "data.xml")
            
            ref = DatasetRef(
                provider='sdmx',
                id='QNA',
                params={}  # No base_url in params
            )
            
            result = provider.fetch(ref, str(tmp_path))
            
            # Verify provider's base_url was used
            call_args = mock_download.call_args
            assert 'sdmx.example.org' in call_args[0][0]
    
    def test_fetch_params_base_url_overrides_provider(self, tmp_path):
        """Test that params base_url overrides provider base_url."""
        provider = SDMXProvider(base_url='https://default.example.org/rest')
        
        with patch('publicdata_ca.providers.sdmx.download_file') as mock_download:
            mock_download.return_value = str(tmp_path / "data.xml")
            
            ref = DatasetRef(
                provider='sdmx',
                id='QNA',
                params={'base_url': 'https://override.example.org/rest'}
            )
            
            result = provider.fetch(ref, str(tmp_path))
            
            # Verify overridden base_url was used
            call_args = mock_download.call_args
            assert 'override.example.org' in call_args[0][0]
