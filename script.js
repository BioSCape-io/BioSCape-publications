$(document).ready(function() {
    // Initialize DataTables
    const table = $('#publicationTable').DataTable({
        scrollX: false, // Disable horizontal scrolling
        scrollY: 9000,   // Set a fixed height for vertical scrolling (adjust as needed)
        scrollCollapse: true, // Enable scrollbars when needed
        paging: false, // Enable pagination
        pageLength: 200, // Number of entries per page
        ordering: true, // Enable sorting
        order: [[4, 'desc']] // Sort by the 5th column (year) in descending order
    });

    // Get unique item types from the table with counts
    function getUniqueItemTypesWithCounts() {
        const itemTypeCounts = {};
        table.column(1).data().each(function(value) {
            itemTypeCounts[value] = (itemTypeCounts[value] || 0) + 1;
        });
        
        // Define custom order
        const customOrder = [
            'Journal Article',
            'Conference Paper',
            'Presentation',
            'Thesis',
            'Computer Program',
            'Dataset',
            'Preprint',
            'Report'
        ];
        
        // Sort by custom order, then add any remaining types not in custom order
        const sorted = customOrder
            .filter(type => type in itemTypeCounts)
            .map(type => ({ type: type, count: itemTypeCounts[type] }));
        
        // Add any remaining types not in custom order
        Object.keys(itemTypeCounts)
            .filter(type => !customOrder.includes(type))
            .sort()
            .forEach(type => {
                sorted.push({ type: type, count: itemTypeCounts[type] });
            });
        
        return sorted;
    }

    // Populate filter checkboxes
    function populateFilters() {
        const itemTypesWithCounts = getUniqueItemTypesWithCounts();
        const filterContainer = $('#itemTypeFilters');
        filterContainer.empty();
        
        itemTypesWithCounts.forEach(function(item) {
            const type = item.type;
            const count = item.count;
            const checkboxId = 'filter-' + type.replace(/\s+/g, '-').toLowerCase();
            const filterOption = $('<div class="filter-option"></div>');
            const checkbox = $('<input type="checkbox" class="item-type-filter" value="' + type + '" id="' + checkboxId + '" checked>')
            const label = $('<label for="' + checkboxId + '">' + type + ' (' + count + ')</label>');
            
            filterOption.append(checkbox);
            filterOption.append(label);
            filterContainer.append(filterOption);
        });
    }

    // Global filter state
    let filterState = {
        selectedTypes: [],
        minYear: 2018,
        maxYear: 2026
    };

    // Custom search function for DataTables
    $.fn.dataTable.ext.search.push(
        function(settings, data, dataIndex) {
            const itemType = data[1];
            const year = parseInt(data[4]) || 0;
            
            // Check year constraint (within range)
            if (year < filterState.minYear || year > filterState.maxYear) {
                return false;
            }
            
            // If no types selected, include all
            if (filterState.selectedTypes.length === 0) {
                return true;
            }
            
            // Check if item type is selected
            return filterState.selectedTypes.includes(itemType);
        }
    );

    // Update button visibility based on filter state
    function updateButtonVisibility() {
        // Show "Show All Years" button only if years are filtered
        if (filterState.minYear !== 2018 || filterState.maxYear !== 2026) {
            $('#showAllYearsBtn').show();
        } else {
            $('#showAllYearsBtn').hide();
        }
    }

    // Filter table based on current filter state
    function filterTable() {
        table.draw();
        updateButtonVisibility();
    }

    // Populate filters on load
    populateFilters();

    // Initialize filter state with all types checked
    const allTypes = [];
    $('#itemTypeFilters .item-type-filter').each(function() {
        allTypes.push($(this).val());
    });
    filterState.selectedTypes = allTypes;

    // Display total item count
    const totalItems = table.rows().count();
    $('#itemCountMessage').html('There are currently ' + totalItems + ' items in the BioSCape product database. This includes journal articles, presentations, reports, and other scholarly outputs. Are we missing something?  Please email <a href="mailto:info@bioscape.io">info@bioscape.io</a>.');

    // Chart instance
    let publicationChart = null;

    // Define colors for each item type
    const itemTypeColors = {
        'Journal Article': 'rgba(0, 35, 149, 0.8)',
        'Conference Paper': 'rgba(54, 114, 191, 0.8)',
        'Presentation': 'rgba(102, 153, 221, 0.8)',
        'Thesis': 'rgba(150, 188, 242, 0.8)',
        'Computer Program': 'rgba(0, 150, 136, 0.8)',
        'Dataset': 'rgba(76, 175, 80, 0.8)',
        'Preprint': 'rgba(255, 152, 0, 0.8)',
        'Report': 'rgba(233, 30, 99, 0.8)'
    };

    // Get year data from visible rows, broken down by item type
    function getYearData() {
        const yearTypeData = {};
        
        // Get all visible rows (filtered data)
        const visibleRows = table.rows({ search: 'applied' }).data();
        
        visibleRows.each(function(row) {
            // Year is in the 5th column (index 4), Item Type is in column 1 (index 1)
            const year = row[4];
            const itemType = row[1];
            
            if (year && year.trim()) {
                if (!yearTypeData[year]) {
                    yearTypeData[year] = {};
                }
                if (!yearTypeData[year][itemType]) {
                    yearTypeData[year][itemType] = 0;
                }
                yearTypeData[year][itemType]++;
            }
        });
        
        // Sort years numerically
        const sortedYears = Object.keys(yearTypeData).sort((a, b) => a - b);
        
        // Get all unique item types from the data
        const allTypes = new Set();
        Object.values(yearTypeData).forEach(yearData => {
            Object.keys(yearData).forEach(type => allTypes.add(type));
        });
        
        // Sort types in custom order
        const customOrder = [
            'Journal Article',
            'Conference Paper',
            'Presentation',
            'Thesis',
            'Computer Program',
            'Dataset',
            'Preprint',
            'Report'
        ];
        const sortedTypes = customOrder.filter(type => allTypes.has(type));
        const remainingTypes = Array.from(allTypes).filter(type => !customOrder.includes(type)).sort();
        const orderedTypes = [...sortedTypes, ...remainingTypes];
        
        // Create datasets for each item type
        const datasets = orderedTypes.map((type, index) => {
            const counts = sortedYears.map(year => yearTypeData[year][type] || 0);
            return {
                label: type,
                data: counts,
                backgroundColor: itemTypeColors[type] || 'rgba(128, 128, 128, 0.8)',
                borderColor: itemTypeColors[type] || 'rgba(128, 128, 128, 1)',
                borderWidth: 0.5
            };
        });
        
        return {
            years: sortedYears,
            datasets: datasets
        };
    }

    // Initialize or update chart
    function updateChart() {
        const yearData = getYearData();
        
        if (!publicationChart) {
            // Create chart
            const ctx = document.getElementById('publicationChart').getContext('2d');
            publicationChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: yearData.years,
                    datasets: yearData.datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: undefined,
                    onClick: function(event, activeElements) {
                        // Handle bar click to filter by year
                        if (activeElements.length > 0) {
                            const clickedElement = activeElements[0];
                            const yearIndex = clickedElement.index;
                            const selectedYear = publicationChart.data.labels[yearIndex];
                            
                            // Set year range to just the clicked year
                            filterState.minYear = parseInt(selectedYear);
                            filterState.maxYear = parseInt(selectedYear);
                            
                            // Update year sliders
                            $('#yearMinSlider').val(filterState.minYear);
                            $('#yearMaxSlider').val(filterState.maxYear);
                            $('#selectedYearDisplay').text(filterState.minYear + ' - ' + filterState.maxYear);
                            
                            // Filter table and update chart
                            filterTable();
                            updateChart();
                            updateButtonVisibility();
                        }
                    },
                    scales: {
                        x: {
                            stacked: true,
                            title: {
                                display: true,
                                text: 'Year'
                            }
                        },
                        y: {
                            stacked: true,
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Outputs'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'left',
                            onClick: function(e, legendItem, legend) {
                                // Get the index of the clicked dataset
                                const datasetIndex = legendItem.datasetIndex;
                                const meta = publicationChart.getDatasetMeta(datasetIndex);
                                
                                // Toggle the visibility of this dataset
                                meta.hidden = !meta.hidden;
                                
                                // Update the filter state based on visible datasets
                                const visibleTypes = [];
                                publicationChart.data.datasets.forEach((dataset, index) => {
                                    const datasetMeta = publicationChart.getDatasetMeta(index);
                                    if (!datasetMeta.hidden) {
                                        visibleTypes.push(dataset.label);
                                    }
                                });
                                
                                // Update filter state and table
                                filterState.selectedTypes = visibleTypes;
                                
                                // Update checkboxes to match
                                $('#itemTypeFilters .item-type-filter').each(function() {
                                    const type = $(this).val();
                                    $(this).prop('checked', visibleTypes.includes(type));
                                });
                                
                                filterTable();
                                publicationChart.update();
                            }
                        }
                    }
                }
            });
        } else {
            // Update existing chart
            publicationChart.data.labels = yearData.years;
            publicationChart.data.datasets = yearData.datasets;
            publicationChart.update();
        }
    }

    // Initialize chart on page load
    updateChart();
    
    // Initialize button visibility
    updateButtonVisibility();

    // Update chart when filters change
    $(document).on('change', '.item-type-filter', function() {
        const selectedTypes = [];
        $('#itemTypeFilters .item-type-filter:checked').each(function() {
            selectedTypes.push($(this).val());
        });
        
        filterState.selectedTypes = selectedTypes;
        
        // Update chart dataset visibility to match checkboxes
        if (publicationChart) {
            publicationChart.data.datasets.forEach(function(dataset, index) {
                const meta = publicationChart.getDatasetMeta(index);
                meta.hidden = !selectedTypes.includes(dataset.label);
            });
        }
        
        filterTable();
        updateChart();
    });

    // Initialize noUiSlider for year range
    $('#yearMinSlider, #yearMaxSlider').on('input', function() {
        const minYear = parseInt($('#yearMinSlider').val());
        const maxYear = parseInt($('#yearMaxSlider').val());
        
        // Ensure min doesn't exceed max
        if (minYear > maxYear) {
            if ($(this).attr('id') === 'yearMinSlider') {
                $('#yearMinSlider').val(maxYear);
                filterState.minYear = maxYear;
            } else {
                $('#yearMaxSlider').val(minYear);
                filterState.maxYear = minYear;
            }
        } else {
            filterState.minYear = minYear;
            filterState.maxYear = maxYear;
        }
        
        $('#selectedYearDisplay').text(filterState.minYear + ' - ' + filterState.maxYear);
        filterTable();
        updateChart();
    });

    // Select All button
    $('#selectAllBtn').on('click', function() {
        $('#itemTypeFilters .item-type-filter').prop('checked', true);
        
        const allTypes = [];
        $('#itemTypeFilters .item-type-filter').each(function() {
            allTypes.push($(this).val());
        });
        filterState.selectedTypes = allTypes;
        
        // Show all chart datasets
        if (publicationChart) {
            publicationChart.data.datasets.forEach(function(dataset, index) {
                const meta = publicationChart.getDatasetMeta(index);
                meta.hidden = false;
            });
        }
        
        filterTable();
        updateChart();
    });

    // Select None button
    $('#selectNoneBtn').on('click', function() {
        $('#itemTypeFilters .item-type-filter').prop('checked', false);
        filterState.selectedTypes = [];
        
        // Hide all chart datasets
        if (publicationChart) {
            publicationChart.data.datasets.forEach(function(dataset, index) {
                const meta = publicationChart.getDatasetMeta(index);
                meta.hidden = true;
            });
        }
        
        filterTable();
        updateChart();
    });

    // Show All Years button
    $('#showAllYearsBtn').on('click', function() {
        filterState.minYear = 2018;
        filterState.maxYear = 2026;
        
        // Reset filter state to include all item types
        const allTypes = getUniqueItemTypesWithCounts().map(item => item.type);
        filterState.selectedTypes = allTypes;
        
        // Show all chart datasets
        if (publicationChart) {
            publicationChart.data.datasets.forEach(function(dataset, index) {
                const meta = publicationChart.getDatasetMeta(index);
                meta.hidden = false;
            });
        }
        
        // Update year sliders
        $('#yearMinSlider').val(2018);
        $('#yearMaxSlider').val(2026);
        $('#selectedYearDisplay').text('2018 - 2026');
        
        // Filter table and update chart
        filterTable();
        updateChart();
    });

    // Show All Item Types button
    $('#showAllItemTypesBtn').on('click', function() {
        // Check all item type checkboxes
        $('#itemTypeFilters .item-type-filter').prop('checked', true);
        
        // Get all types
        const allTypes = [];
        $('#itemTypeFilters .item-type-filter').each(function() {
            allTypes.push($(this).val());
        });
        filterState.selectedTypes = allTypes;
        
        // Show all chart datasets
        if (publicationChart) {
            publicationChart.data.datasets.forEach(function(dataset, index) {
                const meta = publicationChart.getDatasetMeta(index);
                meta.hidden = false;
            });
        }
        
        // Filter table and update chart
        filterTable();
        updateChart();
    });
});
