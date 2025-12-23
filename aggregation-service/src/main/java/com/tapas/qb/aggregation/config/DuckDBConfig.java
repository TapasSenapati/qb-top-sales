package com.tapas.qb.aggregation.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.io.PrintWriter;
import java.sql.Connection;
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
     * Creates a DataSource wrapper for DuckDB.
     * Note: DuckDB is single-writer, so this creates a new connection for each
     * request.
     */
    @Bean(name = "duckdbDataSource")
    public DataSource duckdbDataSource() {
        logger.info("Initializing DuckDB DataSource with path: {}", duckdbPath);
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
     * Creates new connections on demand (DuckDB handles concurrency internally).
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
            if (iface.isInstance(this)) {
                return iface.cast(this);
            }
            throw new SQLException("Cannot unwrap to " + iface);
        }

        @Override
        public boolean isWrapperFor(Class<?> iface) {
            return iface.isInstance(this);
        }
    }
}
