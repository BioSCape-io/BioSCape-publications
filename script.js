// ----------------------------------------------------------------------- //
// Stats dashboard rendering                                               //
// ----------------------------------------------------------------------- //

// Human-friendly country names for the most common country codes we see;
// unknown codes fall through to the raw code.
const COUNTRY_NAMES = {
    US: 'United States',
    ZA: 'South Africa',
    GB: 'United Kingdom',
    DE: 'Germany',
    NL: 'Netherlands',
    CA: 'Canada',
    AU: 'Australia',
    FR: 'France',
    CH: 'Switzerland',
    ES: 'Spain',
    IT: 'Italy',
    BR: 'Brazil',
    NO: 'Norway',
    SE: 'Sweden',
    IE: 'Ireland',
    JP: 'Japan',
    IN: 'India',
    KE: 'Kenya',
    NG: 'Nigeria',
    NZ: 'New Zealand',
    AT: 'Austria',
    BE: 'Belgium',
    DK: 'Denmark',
    FI: 'Finland',
    PT: 'Portugal',
    MX: 'Mexico',
    CN: 'China',
    MZ: 'Mozambique',
    BW: 'Botswana',
    NA: 'Namibia',
    ZW: 'Zimbabwe'
};

function countryLabel(code) {
    return COUNTRY_NAMES[code] || code;
}

// Color palettes aligned with styles.css topic-badge colors.
const TOPIC_COLORS = {
    ecosystem: {
        'Terrestrial': '#588157',
        'Freshwater': '#00b4d8',
        'Estuarine/Coastal': '#2a9d8f',
        'Marine': '#0077b6'
    },
    taxa: {
        'Plants': '#386641',
        'Phytoplankton': '#0096c7',
        'Vocal fauna': '#ae5c1c'
    },
    method: {
        'Field observation': '#023e8a',
        'Remote sensing': '#c1121f',
        'Machine learning': '#ff8500',
        'Molecular / eDNA': '#6d597a',
        'Statistical modeling': '#e9b306',
        'Physics-based modeling': '#264653',
        'Perspective & synthesis': '#6c757d'
    }
};

function renderStatsDashboard(stats) {
    if (!stats) {
        return;
    }

    // Top metric cards.
    document.getElementById('statTotalOutputs').textContent =
        stats.total_outputs.toLocaleString();
    document.getElementById('statOutputsWithDoi').textContent =
        stats.outputs_with_doi.toLocaleString();
    document.getElementById('statUniqueAuthors').textContent =
        stats.unique_authors.toLocaleString();
    document.getElementById('statUsSaPct').textContent =
        stats.us_sa_collab_pct.toFixed(1) + '%';

    // Country breakdown horizontal bar chart. Highlight US and ZA.
    const countries = (stats.country_breakdown || []).slice(0, 12);
    const countryNote = document.getElementById('countryChartNote');
    if (countries.length === 0) {
        countryNote.textContent = 'Author affiliation data not yet available.';
    } else {
        const total = (stats.country_breakdown || [])
            .reduce((sum, c) => sum + c.count, 0);
        countryNote.textContent =
            'Distinct authors per country of institutional affiliation ' +
            '(from ' + stats.outputs_with_doi + ' outputs with DOIs). ' +
            'An author with affiliations in multiple countries is counted once per country.';
        const ctx = document.getElementById('countryChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: countries.map(c => countryLabel(c.country)),
                datasets: [{
                    label: 'Unique authors',
                    data: countries.map(c => c.count),
                    backgroundColor: countries.map(c => {
                        if (c.country === 'US') return '#0a3d91';
                        if (c.country === 'ZA') return '#007a3d';
                        return '#6c757d';
                    })
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                const pct = total ? (100 * ctx.parsed.x / total).toFixed(1) : '0.0';
                                return ctx.parsed.x + ' authors (' + pct + '% of tagged authorships)';
                            }
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, title: { display: true, text: 'Distinct authors' } },
                    y: { ticks: { autoSkip: false } }
                }
            }
        });
    }

    // Collaboration donut.
    const collabData = [
        { label: 'US–South Africa co-authored', value: stats.us_sa_collab_papers, color: '#e63946' },
        { label: 'US only', value: stats.us_only_papers, color: '#0a3d91' },
        { label: 'South Africa only', value: stats.sa_only_papers, color: '#007a3d' },
        { label: 'Other international', value: stats.international_other_papers, color: '#6c757d' }
    ].filter(d => d.value > 0);
    if (collabData.length > 0) {
        const ctx = document.getElementById('collabChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: collabData.map(d => d.label),
                datasets: [{
                    data: collabData.map(d => d.value),
                    backgroundColor: collabData.map(d => d.color)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce((s, v) => s + v, 0);
                                const pct = total ? (100 * ctx.parsed / total).toFixed(1) : '0.0';
                                return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    // Authorships by group × role stacked bar.
    const roleData = stats.authorships_by_group_role;
    const rolesCanvas = document.getElementById('rolesByGroupChart');
    if (roleData && roleData.groups && rolesCanvas) {
        const roleColors = {
            first: '#003295',
            last: '#e63946',
            middle: '#adb5bd'
        };
        const roleLabels = { first: 'First author', last: 'Last author', middle: 'Middle author' };
        const datasets = (roleData.roles || []).map(function(role) {
            return {
                label: roleLabels[role] || role,
                data: roleData.groups.map(function(group) {
                    return (roleData.counts[group] || [])[roleData.roles.indexOf(role)] || 0;
                }),
                backgroundColor: roleColors[role] || '#6c757d'
            };
        });
        new Chart(rolesCanvas.getContext('2d'), {
            type: 'bar',
            data: { labels: roleData.groups, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                const columnTotal = ctx.chart.data.datasets
                                    .reduce(function(s, ds) { return s + (ds.data[ctx.dataIndex] || 0); }, 0);
                                const pct = columnTotal
                                    ? (100 * ctx.parsed.y / columnTotal).toFixed(1)
                                    : '0.0';
                                return ctx.dataset.label + ': ' + ctx.parsed.y +
                                    ' (' + pct + '% of ' + ctx.label + ')';
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: true },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: { display: true, text: 'Authorships' }
                    }
                }
            }
        });
    }

    // Topic distribution donuts.
    const topicMounts = {
        ecosystem: 'ecosystemChart',
        taxa: 'taxaChart',
        method: 'methodChart'
    };
    const dist = stats.topic_distribution || {};
    Object.keys(topicMounts).forEach(function(dim) {
        const canvasId = topicMounts[dim];
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const entries = (dist[dim] || []).filter(e => e.count > 0);
        if (entries.length === 0) return;
        const palette = TOPIC_COLORS[dim] || {};
        new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: entries.map(e => e.category),
                datasets: [{
                    data: entries.map(e => e.count),
                    backgroundColor: entries.map(e => palette[e.category] || '#6c757d')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce((s, v) => s + v, 0);
                                const pct = total ? (100 * ctx.parsed / total).toFixed(1) : '0.0';
                                return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                            }
                        }
                    }
                }
            }
        });
    });
}

$(document).ready(function() {
    // ---------------------------------------------------------------- //
    // Stats dashboard                                                  //
    // ---------------------------------------------------------------- //
    renderStatsDashboard(window.BIOSCAPE_STATS || null);

    // Initialize DataTables
    const table = $('#publicationTable').DataTable({
        scrollX: false, // Disable horizontal scrolling
        scrollY: false,   // Set a fixed height for vertical scrolling (adjust as needed)
        paging: false, // Enable pagination
        pageLength: 250, // Number of entries per page
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

    // Helper to pluralize common item types (fallback: add 's')
    function pluralize(type, count) {
        const mapping = {
            'Thesis': 'Theses',
            'Journal Article': 'Journal Articles',
            'Conference Paper': 'Conference Papers',
            'Presentation': 'Presentations',
            'Computer Program': 'Computer Programs',
            'Dataset': 'Datasets',
            'Preprint': 'Preprints',
            'Report': 'Reports'
        };
        if (mapping[type]) return mapping[type];
        return count === 1 ? type : type + 's';
    }

    // Build a per-type counts list for the message
    const itemTypesWithCounts = getUniqueItemTypesWithCounts();
    const countsList = itemTypesWithCounts
        .map(item => item.count + ' ' + pluralize(item.type, item.count))
        .join(', ');

    $('#itemCountMessage').html('To date, BioSCape has produced ' + totalItems + ' scientific outputs, including ' + countsList + '.');

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
