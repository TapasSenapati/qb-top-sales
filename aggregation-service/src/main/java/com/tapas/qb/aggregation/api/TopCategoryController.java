package com.tapas.qb.aggregation.api;

import com.tapas.qb.aggregation.service.TopCategoryQueryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api")
public class TopCategoryController {

    private final TopCategoryQueryService service;

    public TopCategoryController(TopCategoryQueryService service) {
        this.service = service;
    }

    @Operation(
            summary = "Top categories by sales",
            description = "Returns the top categories for a merchant in a given bucket starting at bucketStart.",
            responses = {
                    @ApiResponse(
                            responseCode = "200",
                            description = "Successful response",
                            content = @Content(
                                    mediaType = "application/json",
                                    schema = @Schema(implementation = TopCategoryResponse.class),
                                    examples = @ExampleObject(
                                            name = "topCategoriesExample",
                                            value = "[{\n  \"categoryId\": 101,\n  \"categoryName\": \"Beverages\",\n  \"totalSalesAmount\": 12345.67,\n  \"totalUnitsSold\": 321,\n  \"orderCount\": 45\n}, {\n  \"categoryId\": 102,\n  \"categoryName\": \"Snacks\",\n  \"totalSalesAmount\": 9876.54,\n  \"totalUnitsSold\": 210,\n  \"orderCount\": 30\n}]"
                                    )
                            )
                    )
            }
    )
    @GetMapping("/top-categories")
    public List<TopCategoryResponse> topCategories(
            @Parameter(description = "Merchant identifier", example = "1")
            @RequestParam Long merchantId,
            @Parameter(description = "Aggregation bucket type", example = "DAY")
            @RequestParam String bucketType,
            @Parameter(description = "Start of the bucket (ISO-8601)", example = "2024-01-01T00:00:00Z")
            @RequestParam Instant bucketStart,
            @Parameter(description = "Max number of categories to return", example = "5")
            @RequestParam(defaultValue = "5") int limit
    ) {
        return service.topCategories(
                        merchantId,
                        bucketType,
                        bucketStart,
                        limit
                )
                .stream()
                .map(TopCategoryResponse::from)
                .toList();
    }
}
