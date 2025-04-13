# DVLA Vehicle Enquiry Service API Tools

This package provides tools for interacting with the DVLA Vehicle Enquiry Service API to retrieve vehicle information.

## Features

- Query vehicle details by registration number
- Process multiple registrations from a CSV file
- Save results in CSV, Excel, or JSON format
- Detailed error handling and logging

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - requests
  - pandas

## Installation

1. Clone or download this repository
2. Install the required packages:

```bash
pip install requests pandas
```

3. Make the scripts executable:

```bash
chmod +x dvla_vehicle_enquiry.py dvla_batch_processor.py
```

## Configuration

The scripts use the API key provided in the command line arguments or the default key defined in the scripts. You can update the default API key in the scripts if needed.

Your API key: `AXPW4KqAyS4G7eb53rav46TzufDC3a1v2yJUCJAi`

## Usage

### Single Vehicle Enquiry

To query information for a single vehicle:

```bash
python dvla_vehicle_enquiry.py AB12CDE
```

Options:
- `--api-key KEY`: Specify your DVLA API key (optional)
- `--json`: Output in JSON format
- `--save-json`: Save results to a JSON file
- `--save-csv`: Save results to a CSV file
- `--output FILENAME`: Specify the output filename

Example:

```bash
python dvla_vehicle_enquiry.py AB12CDE --save-json --output vehicle_details.json
```

### Batch Processing

To process multiple vehicle registrations from a CSV file:

```bash
python dvla_batch_processor.py vehicle_registrations.csv
```

Options:
- `--api-key KEY`: Specify your DVLA API key (optional)
- `--column NAME`: Specify the column name containing registration numbers
- `--output FILENAME`: Specify the output filename
- `--format {csv,excel,json}`: Specify the output format (default: csv)
- `--no-header`: Indicate that the CSV file has no header row

Example:

```bash
python dvla_batch_processor.py vehicle_registrations.csv --column Registration --format excel --output vehicle_details.xlsx
```

## API Rate Limiting

The DVLA Vehicle Enquiry Service API has rate limits based on your registration. The batch processor includes a delay between requests to avoid hitting these limits. You can adjust the `RATE_LIMIT_DELAY` constant in the script if needed.

## Error Handling

Both scripts include comprehensive error handling and logging. Errors are logged to:
- `dvla_enquiry.log` for the single vehicle enquiry script
- `dvla_batch.log` for the batch processor

## Data Fields

The API may return the following fields for each vehicle:

- registrationNumber
- taxStatus
- taxDueDate
- motStatus
- make
- yearOfManufacture
- engineCapacity
- co2Emissions
- fuelType
- markedForExport
- colour
- typeApproval
- dateOfLastV5CIssued
- motExpiryDate
- wheelplan
- monthOfFirstRegistration
- artEndDate
- revenueWeight
- euroStatus
- realDrivingEmissions

Note that some fields may not be available for all vehicles.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- This tool uses the [DVLA Vehicle Enquiry Service API](https://developer-portal.driver-vehicle-licensing.api.gov.uk/apis/vehicle-enquiry-service/vehicle-enquiry-service-description.html)
- Based on the [DVLA-Vehicle-Enquiry-Service](https://github.com/jampez77/DVLA-Vehicle-Enquiry-Service) project by jampez77
