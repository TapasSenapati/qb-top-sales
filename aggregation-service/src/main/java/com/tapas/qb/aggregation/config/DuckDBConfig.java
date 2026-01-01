package com.tapas.qb.aggregation.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;
import jakarta.annotation.PostConstruct;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.io.PrintWriter;
import java.sql.SQLFeatureNotSupportedException;

/**
 * Configuration for DuckDB connection.
 * DuckDB is used for analytical data (category_sales_agg, processed_events,
 * forecasts).
 */
@Configuration
public class DuckDBConfig {

    private static final Logger logger = LoggerFactory.getLogger(DuckDBConfig.class);

    @Value("${duckdb.path:/data/forecasting.duckdb}")
    private String duckdbPath;

    /**
     * Initialize DuckDB schema on startup using @PostConstruct.
     * This ensures tables exist before any queries are run.
     */
    @PostConstruct
    public void initializeDuckDBSchema() {
        logger.info("Initializing DuckDB schema at path: {}", duckdbPath);
        try (Connection conn = DriverManager.getConnection("jdbc:duckdb:" + duckdbPath)) {
            try (var stmt = conn.createStatement()) {
                // Create sequences
                stmt.execute("CREATE SEQUENCE IF NOT EXISTS category_sales_agg_id_seq START 1");
                logger.info("Created sequence: category_sales_agg_id_seq");

                // Create category_sales_agg table
                stmt.execute("""
                        CREATE TABLE IF NOT EXISTS category_sales_agg (
                            id BIGINT PRIMARY KEY,
                            merchant_id BIGINT NOT NULL,
                            category_id BIGINT NOT NULL,
                            bucket_type VARCHAR NOT NULL,
                            bucket_start TIMESTAMPTZ NOT NULL,
                            bucket_end TIMESTAMPTZ NOT NULL,
                            total_sales_amount DECIMAL(18,2) DEFAULT 0,
                            total_units_sold BIGINT DEFAULT 0,
                            order_count BIGINT DEFAULT 0,
                            updated_at TIMESTAMPTZ DEFAULT now()
                        )
                        """);
                logger.info("Created table: category_sales_agg");

                // Create unique index for upserts
                stmt.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_category_sales_bucket
                        ON category_sales_agg (merchant_id, category_id, bucket_type, bucket_start)
                        """);
                logger.info("Created index: uq_category_sales_bucket");

                // Create processed_events table for idempotency
                stmt.execute("""
                        CREATE TABLE IF NOT EXISTS processed_events (
                            order_id BIGINT PRIMARY KEY,
                            processed_at TIMESTAMPTZ NOT NULL
                        )
                        """);
                logger.info("Created table: processed_events");

                logger.info("DuckDB schema initialized successfully");
            }
        } catch (SQLException e) {
            logger.error("Failed to initialize DuckDB schema", e);
            throw new RuntimeException("DuckDB schema initialization failed", e);
        }
    }

    /**
     * Creates a DataSource wrapper for DuckDB.
     */
    @Bean(name = "duckdbDataSource")
    public DataSource duckdbDataSource() {
        logger.info("Creating DuckDB DataSource with path: {}", duckdbPath);
        return new DuckDBDataSource(duckdbPath);
    }

    /**
     * JdbcTemplate configured for DuckDB operations.
     */
    @Bean(name = "duckdbJdbcTemplate")
    public JdbcTemplate duckdbJdbcTemplate() {
        return new JdbcTemplate(duckdbDataSource());
    }

    /**
     * Simple DataSource wrapper for DuckDB.
     */
    private static class DuckDBDataSource implements DataSource {
        private final String dbPath;
        private PrintWriter logWriter;
        private int loginTimeout = 0;

        public DuckDBDataSource(String dbPath) {
            this.dbPath = dbPath;
        }

        @Override
        public Connection getConnection() throws SQLException {
            return DriverManager.getConnection("jdbc:duckdb:" + dbPath);
        }

        @Override
        public Connection getConnection(String username, String password) throws SQLException {
            return getConnection();
        }

        @Override
        public PrintWriter getLogWriter() {
            return logWriter;
        }

        @Override
        public void setLogWriter(PrintWriter out) {
            this.logWriter = out;
        }

        @Override
        public void setLoginTimeout(int seconds) {
            this.loginTimeout = seconds;
        }

        @Override
        public int getLoginTimeout() {
            return loginTimeout;
        }

        @Override
        public java.util.logging.Logger getParentLogger() throws SQLFeatureNotSupportedException {
            return java.util.logging.Logger.getLogger(java.util.logging.Logger.GLOBAL_LOGGER_NAME);
        }

        @Override
        public <T> T unwrap(Class<T> iface) throws SQLException {
            if (iface.isInstance(this))
                return iface.cast(this);
            throw new SQLException("Cannot unwrap to " + iface);
        }

        @Override
        public boolean isWrapperFor(Class<?> iface) {
            return iface.isInstance(this);
        }
    }
}
