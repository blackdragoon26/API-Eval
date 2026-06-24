"""
Compatibility wrapper for the final FortyGuard API audit.

The original exploratory test suite was superseded after the final endpoint
audit confirmed the correct documented Heatmap request shape is a GeoJSON
FeatureCollection. Keep this filename for reviewers who expect an
`api_test_suite.py`, but delegate to the corrected audit script.

Usage:
    export FORTYGUARD_API_KEY="..."
    python scripts/api_test_suite.py
"""

from final_api_endpoint_audit import main


if __name__ == "__main__":
    main()
