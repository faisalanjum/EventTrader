"""Scanner operations."""

from defusedxml import ElementTree
from ib_async.objects import ScannerSubscription, TagValue

from .client import IBClient
from app.core.setup_logging import logger
from app.models.scanner import ScannerRequest


class ScannerClient(IBClient):
  """Scanner operations.

  Available public methods:
    - get_scanner_instrument_codes: get scanner instrument codes
    - get_scanner_location_codes: get scanner location codes
    - get_scanner_filter_codes: get scanner filter codes
    - get_scanner_results: get scanner results
  """

  async def get_scanner_instrument_codes(self) -> list[str]:
    """Get scanner instrument codes."""
    try:
      await self._connect()
      xml_parameters = await self.ib.reqScannerParametersAsync()
      tree = ElementTree.fromstring(xml_parameters)
      tags = [elem.text for elem in tree.findall(".//Instrument/type")]
    except Exception as e:
      logger.error("Error getting scanner instrument codes: {}", str(e))
      raise
    else:
      return tags

  async def get_scanner_location_codes(self) -> list[str]:
    """Get scanner location codes."""
    try:
      await self._connect()
      xml_parameters = await self.ib.reqScannerParametersAsync()
      tree = ElementTree.fromstring(xml_parameters)
      tags = [elem.text for elem in tree.findall(".//Location/locationCode")]
    except Exception as e:
      logger.error("Error getting scanner location codes: {}", str(e))
      raise
    else:
      return tags

  async def get_scanner_filter_codes(self) -> list[str]:
    """Get scanner filter codes."""
    try:
      await self._connect()
      xml_parameters = await self.ib.reqScannerParametersAsync()
      tree = ElementTree.fromstring(xml_parameters)
      tags = [elem.text for elem in tree.findall(".//AbstractField/code")]
    except Exception as e:
      logger.error("Error getting scanner filter codes: {}", str(e))
      raise
    else:
      return tags

  async def get_scanner_scan_codes(self) -> list[str]:
    """Get scanner scan codes."""
    try:
      await self._connect()
      xml_parameters = await self.ib.reqScannerParametersAsync()
      tree = ElementTree.fromstring(xml_parameters)
      tags = [elem.text for elem in tree.findall(".//scanCode")]
    except Exception as e:
      logger.error("Error getting scanner scan codes: {}", str(e))
      raise
    else:
      return tags

  async def get_scanner_results(self, scanner_request: ScannerRequest) -> list[str]:
    """Get scanner results.

    Args:
      scanner_request: Scanner request object.


    Returns:
      List of symbols for the given scanner results.

    """
    try:
      cleaned_tags = [
        TagValue(tag.split("=")[0], tag.split("=")[1])
        for tag in scanner_request.get_filter_codes()
      ]

      await self._connect()
      sub_object = ScannerSubscription(
        numberOfRows=scanner_request.max_results,
        instrument=scanner_request.instrument_code,
        locationCode=scanner_request.location_code,
        scanCode=scanner_request.scan_code,
      )
      scanner_data = await self.ib.reqScannerDataAsync(sub_object, [], cleaned_tags)

      symbols = [row.contractDetails.contract.symbol for row in scanner_data]
    except Exception as e:
      logger.error("Error getting scanner results: {}", str(e))
      raise
    else:
      return symbols
