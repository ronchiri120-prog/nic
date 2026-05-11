"""
Health check endpoint called by load balancer and monitoring.
Usage: python manage.py healthcheck
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run system health checks"

    def handle(self, *args, **options):
        errors = []

        # DB
        try:
            from django.db import connection
            connection.ensure_connection()
            self.stdout.write("  ✓ PostgreSQL: connected")
        except Exception as e:
            errors.append(f"PostgreSQL: {e}")

        # Redis
        try:
            import redis
            from django.conf import settings
            r = redis.from_url(settings.CELERY_BROKER_URL)
            r.ping()
            self.stdout.write("  ✓ Redis: connected")
        except Exception as e:
            errors.append(f"Redis: {e}")

        # Migrations
        try:
            from django.db.migrations.executor import MigrationExecutor
            from django.db import connections
            conn = connections["default"]
            executor = MigrationExecutor(conn)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if plan:
                errors.append(f"Unapplied migrations: {len(plan)}")
            else:
                self.stdout.write("  ✓ Migrations: all applied")
        except Exception as e:
            errors.append(f"Migrations check: {e}")

        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f"  ✗ {e}"))
            raise CommandError("Health check failed")
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ All health checks passed"))
