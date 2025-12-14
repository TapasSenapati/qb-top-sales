package com.tapas.qb.forecasting.api;

import com.tapas.qb.forecasting.service.TopCategoryQueryService;
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

    @GetMapping("/top-categories")
    public List<TopCategoryResponse> topCategories(
            @RequestParam Long merchantId,
            @RequestParam String bucketType,
            @RequestParam Instant bucketStart,
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
