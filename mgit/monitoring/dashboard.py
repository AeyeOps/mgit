"""Grafana dashboard and alerting configuration for mgit.

This module provides pre-built Grafana dashboards and Prometheus
alerting rules for comprehensive mgit monitoring.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


def create_grafana_dashboard(
    datasource_name: str = "Prometheus",
    refresh_interval: str = "30s"
) -> Dict[str, Any]:
    """Create a comprehensive Grafana dashboard for mgit monitoring.
    
    Args:
        datasource_name: Name of the Prometheus datasource
        refresh_interval: Dashboard refresh interval
        
    Returns:
        Grafana dashboard JSON configuration
    """
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "mgit - Multi-Git Tool Monitoring",
            "description": "Comprehensive monitoring dashboard for mgit operations",
            "tags": ["mgit", "git", "devops", "monitoring"],
            "timezone": "browser",
            "refresh": refresh_interval,
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
                "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
            },
            "panels": [
                # Row: Overview
                {
                    "title": "Overview",
                    "type": "row",
                    "collapsed": False,
                    "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
                    "id": 1
                },
                
                # Health Status
                {
                    "title": "System Health",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "mgit_health_overall",
                            "legendFormat": "Health Status",
                            "datasource": datasource_name
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "yellow", "value": 0.8},
                                    {"color": "green", "value": 1}
                                ]
                            },
                            "mappings": [
                                {"options": {"0": {"text": "Unhealthy"}}, "type": "value"},
                                {"options": {"1": {"text": "Healthy"}}, "type": "value"}
                            ]
                        }
                    },
                    "gridPos": {"h": 6, "w": 4, "x": 0, "y": 1},
                    "id": 2
                },
                
                # Health Percentage
                {
                    "title": "Health Percentage",
                    "type": "gauge",
                    "targets": [
                        {
                            "expr": "mgit_health_percentage",
                            "legendFormat": "Health %",
                            "datasource": datasource_name
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "yellow", "value": 70},
                                    {"color": "green", "value": 90}
                                ]
                            },
                            "unit": "percent",
                            "min": 0,
                            "max": 100
                        }
                    },
                    "gridPos": {"h": 6, "w": 4, "x": 4, "y": 1},
                    "id": 3
                },
                
                # Operations Rate
                {
                    "title": "Operations Rate",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "rate(mgit_operations_total[5m])",
                            "legendFormat": "Ops/sec",
                            "datasource": datasource_name
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ops",
                            "decimals": 2
                        }
                    },
                    "gridPos": {"h": 6, "w": 4, "x": 8, "y": 1},
                    "id": 4
                },
                
                # Success Rate
                {
                    "title": "Success Rate",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "rate(mgit_operations_success_total[5m]) / rate(mgit_operations_total[5m]) * 100",
                            "legendFormat": "Success %",
                            "datasource": datasource_name
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "yellow", "value": 90},
                                    {"color": "green", "value": 98}
                                ]
                            },
                            "unit": "percent",
                            "min": 0,
                            "max": 100
                        }
                    },
                    "gridPos": {"h": 6, "w": 4, "x": 12, "y": 1},
                    "id": 5
                },
                
                # Concurrent Operations
                {
                    "title": "Concurrent Operations",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "mgit_concurrent_operations",
                            "legendFormat": "Concurrent",
                            "datasource": datasource_name
                        }
                    ],
                    "gridPos": {"h": 6, "w": 4, "x": 16, "y": 1},
                    "id": 6
                },
                
                # Repositories Processed
                {
                    "title": "Repositories Processed",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "mgit_repositories_processed",
                            "legendFormat": "Total Repos",
                            "datasource": datasource_name
                        }
                    ],
                    "gridPos": {"h": 6, "w": 4, "x": 20, "y": 1},
                    "id": 7
                },
                
                # Row: Operations
                {
                    "title": "Operations",
                    "type": "row",
                    "collapsed": False,
                    "gridPos": {"h": 1, "w": 24, "x": 0, "y": 7},
                    "id": 8
                },
                
                # Operations Over Time
                {
                    "title": "Operations Over Time",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(mgit_operations_total[1m])",
                            "legendFormat": "Total Operations",
                            "datasource": datasource_name
                        },
                        {
                            "expr": "rate(mgit_operations_success_total[1m])",
                            "legendFormat": "Successful Operations",
                            "datasource": datasource_name
                        },
                        {
                            "expr": "rate(mgit_operations_failure_total[1m])",
                            "legendFormat": "Failed Operations",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Operations/sec",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "id": 9
                },
                
                # Operations by Type
                {
                    "title": "Operations by Type",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(mgit_operations_total[1m]) by (operation)",
                            "legendFormat": "{{operation}}",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Operations/sec",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "id": 10
                },
                
                # Row: Performance
                {
                    "title": "Performance",
                    "type": "row",
                    "collapsed": False,
                    "gridPos": {"h": 1, "w": 24, "x": 0, "y": 16},
                    "id": 11
                },
                
                # Operation Duration Percentiles
                {
                    "title": "Operation Duration Percentiles",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.50, rate(mgit_performance_operation_duration_seconds_bucket[5m]))",
                            "legendFormat": "50th percentile",
                            "datasource": datasource_name
                        },
                        {
                            "expr": "histogram_quantile(0.95, rate(mgit_performance_operation_duration_seconds_bucket[5m]))",
                            "legendFormat": "95th percentile",
                            "datasource": datasource_name
                        },
                        {
                            "expr": "histogram_quantile(0.99, rate(mgit_performance_operation_duration_seconds_bucket[5m]))",
                            "legendFormat": "99th percentile",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Duration (seconds)",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 17},
                    "id": 12
                },
                
                # Git Operations Duration
                {
                    "title": "Git Operations Duration",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(mgit_git_clone_duration_seconds_bucket[5m]))",
                            "legendFormat": "Clone P95",
                            "datasource": datasource_name
                        },
                        {
                            "expr": "histogram_quantile(0.95, rate(mgit_git_pull_duration_seconds_bucket[5m]))",
                            "legendFormat": "Pull P95",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Duration (seconds)",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 17},
                    "id": 13
                },
                
                # Row: Providers
                {
                    "title": "Providers",
                    "type": "row",
                    "collapsed": False,
                    "gridPos": {"h": 1, "w": 24, "x": 0, "y": 25},
                    "id": 14
                },
                
                # API Requests by Provider
                {
                    "title": "API Requests by Provider",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(mgit_api_requests_total[1m]) by (provider)",
                            "legendFormat": "{{provider}}",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Requests/sec",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 8, "x": 0, "y": 26},
                    "id": 15
                },
                
                # API Response Times
                {
                    "title": "API Response Times",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.95, rate(mgit_api_request_duration_seconds_bucket[5m])) by (provider)",
                            "legendFormat": "{{provider}} P95",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Duration (seconds)",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 8, "x": 8, "y": 26},
                    "id": 16
                },
                
                # Rate Limits and Errors
                {
                    "title": "Rate Limits and Errors",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(mgit_provider_rate_limit_hits_total[1m]) by (provider)",
                            "legendFormat": "{{provider}} Rate Limits",
                            "datasource": datasource_name
                        },
                        {
                            "expr": "rate(mgit_api_errors_total[1m]) by (provider)",
                            "legendFormat": "{{provider}} Errors",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Events/sec",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 8, "x": 16, "y": 26},
                    "id": 17
                },
                
                # Row: Authentication
                {
                    "title": "Authentication",
                    "type": "row",
                    "collapsed": False,
                    "gridPos": {"h": 1, "w": 24, "x": 0, "y": 34},
                    "id": 18
                },
                
                # Authentication Success Rate
                {
                    "title": "Authentication Success Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(mgit_auth_success_total[5m]) / rate(mgit_auth_attempts_total[5m]) * 100 by (provider)",
                            "legendFormat": "{{provider}} Success Rate",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Success Rate (%)",
                            "min": 0,
                            "max": 100
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 35},
                    "id": 19
                },
                
                # Authentication Attempts
                {
                    "title": "Authentication Attempts",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(mgit_auth_attempts_total[1m]) by (provider)",
                            "legendFormat": "{{provider}} Attempts",
                            "datasource": datasource_name
                        },
                        {
                            "expr": "rate(mgit_auth_failures_total[1m]) by (provider)",
                            "legendFormat": "{{provider}} Failures",
                            "datasource": datasource_name
                        }
                    ],
                    "yAxes": [
                        {
                            "label": "Attempts/sec",
                            "min": 0
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 35},
                    "id": 20
                }
            ]
        },
        "overwrite": True
    }
    
    return dashboard


def create_alert_rules(namespace: str = "mgit") -> List[Dict[str, Any]]:
    """Create Prometheus alerting rules for mgit monitoring.
    
    Args:
        namespace: Namespace for the alert rules
        
    Returns:
        List of Prometheus alerting rule configurations
    """
    rules = [
        {
            "groups": [
                {
                    "name": f"{namespace}_health",
                    "rules": [
                        {
                            "alert": "MgitUnhealthy",
                            "expr": "mgit_health_overall == 0",
                            "for": "1m",
                            "labels": {
                                "severity": "critical",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit system is unhealthy",
                                "description": "The mgit system overall health status is unhealthy. Check individual health checks for details."
                            }
                        },
                        {
                            "alert": "MgitHealthDegraded",
                            "expr": "mgit_health_percentage < 80",
                            "for": "5m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit health is degraded",
                                "description": "mgit health percentage is {{ $value }}%, which is below the 80% threshold."
                            }
                        },
                        {
                            "alert": "MgitHealthCheckFailing",
                            "expr": "mgit_health_check_status == 0",
                            "for": "2m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit health check {{ $labels.check }} is failing",
                                "description": "Health check {{ $labels.check }} has been failing for more than 2 minutes."
                            }
                        }
                    ]
                },
                {
                    "name": f"{namespace}_operations",
                    "rules": [
                        {
                            "alert": "MgitHighFailureRate",
                            "expr": "rate(mgit_operations_failure_total[5m]) / rate(mgit_operations_total[5m]) > 0.1",
                            "for": "2m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit has high operation failure rate",
                                "description": "mgit operation failure rate is {{ $value | humanizePercentage }} over the last 5 minutes."
                            }
                        },
                        {
                            "alert": "MgitOperationStalled",
                            "expr": "rate(mgit_operations_total[5m]) == 0 and mgit_concurrent_operations > 0",
                            "for": "10m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit operations appear to be stalled",
                                "description": "No operations have completed in the last 5 minutes, but there are {{ $value }} concurrent operations running."
                            }
                        },
                        {
                            "alert": "MgitSlowOperations",
                            "expr": "histogram_quantile(0.95, rate(mgit_performance_operation_duration_seconds_bucket[5m])) > 300",
                            "for": "5m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit operations are running slowly",
                                "description": "95th percentile operation duration is {{ $value }}s, which exceeds the 300s threshold."
                            }
                        }
                    ]
                },
                {
                    "name": f"{namespace}_providers",
                    "rules": [
                        {
                            "alert": "MgitAPIErrors",
                            "expr": "rate(mgit_api_errors_total[5m]) > 0.1",
                            "for": "2m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit is experiencing API errors",
                                "description": "API error rate for {{ $labels.provider }} is {{ $value }} errors/sec."
                            }
                        },
                        {
                            "alert": "MgitRateLimitHit",
                            "expr": "rate(mgit_provider_rate_limit_hits_total[1m]) > 0",
                            "for": "0m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit hit rate limit for {{ $labels.provider }}",
                                "description": "Rate limit hit for provider {{ $labels.provider }} at {{ $value }} hits/min."
                            }
                        },
                        {
                            "alert": "MgitSlowAPIResponses",
                            "expr": "histogram_quantile(0.95, rate(mgit_api_request_duration_seconds_bucket[5m])) > 30",
                            "for": "5m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit API responses are slow",
                                "description": "95th percentile API response time for {{ $labels.provider }} is {{ $value }}s."
                            }
                        }
                    ]
                },
                {
                    "name": f"{namespace}_authentication",
                    "rules": [
                        {
                            "alert": "MgitAuthenticationFailures",
                            "expr": "rate(mgit_auth_failures_total[5m]) > 0.01",
                            "for": "2m",
                            "labels": {
                                "severity": "warning",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit is experiencing authentication failures",
                                "description": "Authentication failure rate for {{ $labels.provider }} is {{ $value }} failures/sec."
                            }
                        }
                    ]
                },
                {
                    "name": f"{namespace}_performance",
                    "rules": [
                        {
                            "alert": "MgitPerformanceAnomaly",
                            "expr": "rate(mgit_performance_anomalies_total[5m]) > 0",
                            "for": "1m",
                            "labels": {
                                "severity": "info",
                                "service": "mgit"
                            },
                            "annotations": {
                                "summary": "mgit performance anomaly detected",
                                "description": "Performance anomaly detected for operation {{ $labels.operation }}: {{ $labels.type }}."
                            }
                        }
                    ]
                }
            ]
        }
    ]
    
    return rules


def save_dashboard_config(dashboard_config: Dict[str, Any], 
                         output_path: Path) -> None:
    """Save Grafana dashboard configuration to file.
    
    Args:
        dashboard_config: Dashboard configuration dictionary
        output_path: Path to save the configuration
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(dashboard_config, f, indent=2)


def save_alert_rules(alert_rules: List[Dict[str, Any]], 
                    output_path: Path) -> None:
    """Save Prometheus alert rules to file.
    
    Args:
        alert_rules: List of alert rule configurations
        output_path: Path to save the rules
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Prometheus expects YAML format
    import yaml
    
    with open(output_path, 'w') as f:
        yaml.dump(alert_rules[0], f, default_flow_style=False)


def create_monitoring_configuration(output_dir: Path,
                                  datasource_name: str = "Prometheus",
                                  namespace: str = "mgit") -> None:
    """Create complete monitoring configuration files.
    
    Args:
        output_dir: Directory to save configuration files
        datasource_name: Name of the Prometheus datasource
        namespace: Namespace for alert rules
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create Grafana dashboard
    dashboard = create_grafana_dashboard(datasource_name)
    save_dashboard_config(dashboard, output_dir / "grafana-dashboard.json")
    
    # Create alert rules
    rules = create_alert_rules(namespace)
    save_alert_rules(rules, output_dir / "prometheus-alerts.yml")
    
    # Create docker-compose for monitoring stack
    docker_compose = {
        "version": "3.8",
        "services": {
            "prometheus": {
                "image": "prom/prometheus:latest",
                "container_name": "mgit-prometheus",
                "ports": ["9090:9090"],
                "volumes": [
                    "./prometheus.yml:/etc/prometheus/prometheus.yml",
                    "./prometheus-alerts.yml:/etc/prometheus/alerts.yml"
                ],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--storage.tsdb.retention.time=200h",
                    "--web.enable-lifecycle"
                ]
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "container_name": "mgit-grafana",
                "ports": ["3000:3000"],
                "environment": {
                    "GF_SECURITY_ADMIN_PASSWORD": "admin"
                },
                "volumes": [
                    "grafana-storage:/var/lib/grafana"
                ]
            }
        },
        "volumes": {
            "grafana-storage": {}
        }
    }
    
    with open(output_dir / "docker-compose.yml", 'w') as f:
        import yaml
        yaml.dump(docker_compose, f, default_flow_style=False)
    
    # Create Prometheus configuration
    prometheus_config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "rule_files": [
            "prometheus-alerts.yml"
        ],
        "scrape_configs": [
            {
                "job_name": "mgit",
                "static_configs": [
                    {
                        "targets": ["host.docker.internal:8080"]
                    }
                ],
                "metrics_path": "/metrics",
                "scrape_interval": "15s"
            }
        ]
    }
    
    with open(output_dir / "prometheus.yml", 'w') as f:
        import yaml
        yaml.dump(prometheus_config, f, default_flow_style=False)
    
    # Create README with setup instructions
    readme_content = """# mgit Monitoring Setup

This directory contains the complete monitoring configuration for mgit.

## Files

- `grafana-dashboard.json`: Grafana dashboard configuration
- `prometheus-alerts.yml`: Prometheus alerting rules
- `docker-compose.yml`: Docker Compose for monitoring stack
- `prometheus.yml`: Prometheus configuration

## Quick Start

1. Start the monitoring stack:
   ```bash
   docker-compose up -d
   ```

2. Access Grafana at http://localhost:3000 (admin/admin)

3. Import the dashboard from `grafana-dashboard.json`

4. Configure mgit to expose metrics on port 8080

## Metrics Endpoint

Ensure mgit is configured to expose metrics:

```python
from mgit.monitoring import setup_metrics, get_metrics_collector

# In your mgit application
setup_metrics()
collector = get_metrics_collector()

# Expose metrics endpoint (example with Flask)
from flask import Flask, Response
app = Flask(__name__)

@app.route('/metrics')
def metrics():
    return Response(
        collector.export_prometheus(),
        mimetype='text/plain'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

## Health Checks

Health check endpoints:

- `/health` - Overall health status
- `/health/ready` - Readiness probe (for Kubernetes)
- `/health/live` - Liveness probe (for Kubernetes)

## Alerts

The following alerts are configured:

- **MgitUnhealthy**: System overall health is down
- **MgitHealthDegraded**: Health percentage below 80%
- **MgitHighFailureRate**: Operation failure rate above 10%
- **MgitAPIErrors**: API error rate too high
- **MgitRateLimitHit**: Rate limits being hit
- **MgitSlowOperations**: Operations taking too long
- **MgitAuthenticationFailures**: Authentication failures occurring

## Customization

Edit the configuration files to:

- Adjust alert thresholds
- Add custom metrics
- Modify dashboard panels
- Configure notification channels
"""
    
    with open(output_dir / "README.md", 'w') as f:
        f.write(readme_content)