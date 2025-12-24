"""Main entry point for EasyScale daemon."""

import argparse
import logging
import sys
from pathlib import Path

from easyscale.controller.daemon import DaemonConfig, create_daemon
from easyscale.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="EasyScale - Kubernetes time-based pod scaling daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with rules from directory
  python -m easyscale --rules-dir /etc/easyscale/rules

  # Run in dry-run mode
  python -m easyscale --rules-dir ./rules --dry-run

  # Run with custom check interval
  python -m easyscale --rules-dir ./rules --check-interval 30

  # Run with local kubeconfig (for development)
  python -m easyscale --rules-dir ./rules --kubeconfig
        """,
    )

    parser.add_argument(
        "--rules-dir",
        type=str,
        help="Directory containing ScalingRule YAML files",
    )

    parser.add_argument(
        "--check-interval",
        type=int,
        default=60,
        help="Seconds between evaluation cycles (default: 60)",
    )

    parser.add_argument(
        "--cooldown",
        type=int,
        default=60,
        help="Minimum seconds between scaling operations for same resource (default: 60)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Enable dry-run mode (evaluate rules but don't scale resources)",
    )

    parser.add_argument(
        "--kubeconfig",
        action="store_true",
        help="Use local kubeconfig instead of in-cluster config",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--log-format",
        type=str,
        default="text",
        choices=["text", "json"],
        help="Log output format (default: text)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="EasyScale 0.1.0",
    )

    return parser.parse_args()


def validate_args(args):
    """
    Validate command-line arguments.

    Args:
        args: Parsed arguments

    Returns:
        True if valid, False otherwise
    """
    if args.check_interval < 1:
        logger.error("Check interval must be at least 1 second")
        return False

    if args.cooldown < 0:
        logger.error("Cooldown must be non-negative")
        return False

    if args.rules_dir:
        rules_path = Path(args.rules_dir)
        if not rules_path.exists():
            logger.error(f"Rules directory does not exist: {args.rules_dir}")
            return False
        if not rules_path.is_dir():
            logger.error(f"Rules path is not a directory: {args.rules_dir}")
            return False

    return True


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()

    # Setup logging
    setup_logging(
        level=args.log_level,
        format_type=args.log_format,
    )

    logger.info("=" * 60)
    logger.info("EasyScale - Kubernetes Time-Based Pod Scaling Daemon")
    logger.info("=" * 60)

    # Validate arguments
    if not validate_args(args):
        sys.exit(1)

    # Log configuration
    logger.info("Configuration:")
    logger.info(f"  Rules directory: {args.rules_dir or '(none)'}")
    logger.info(f"  Check interval: {args.check_interval}s")
    logger.info(f"  Cooldown period: {args.cooldown}s")
    logger.info(f"  Dry-run mode: {args.dry_run}")
    logger.info(f"  Kubernetes config: {'kubeconfig' if args.kubeconfig else 'in-cluster'}")
    logger.info(f"  Log level: {args.log_level}")
    logger.info(f"  Log format: {args.log_format}")

    if args.dry_run:
        logger.warning("⚠️  DRY-RUN MODE ENABLED - No actual scaling will occur")

    # Create daemon configuration
    config = DaemonConfig(
        check_interval=args.check_interval,
        cooldown_seconds=args.cooldown,
        dry_run=args.dry_run,
        in_cluster=not args.kubeconfig,
        rules_directory=args.rules_dir,
    )

    try:
        # Create and start daemon
        logger.info("Initializing EasyScale daemon...")
        daemon = create_daemon(config)

        logger.info("Starting daemon main loop...")
        daemon.run()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
