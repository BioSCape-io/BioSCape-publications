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

    // Filter table based on selected checkboxes
    function filterTable() {
        const selectedTypes = [];
        $('#itemTypeFilters .item-type-filter:checked').each(function() {
            selectedTypes.push($(this).val());
        });

        if (selectedTypes.length === 0) {
            table.column(1).search('').draw();
            return;
        }

        // Create a regex pattern for matching multiple values
        const pattern = selectedTypes.map(type => '^' + type + '$').join('|');
        table.column(1).search(pattern, true, false).draw();
    }

    // Populate filters on load
    populateFilters();

    // Add event listener for filter changes
    $(document).on('change', '.item-type-filter', function() {
        filterTable();
    });

    // Select All button
    $('#selectAllBtn').on('click', function() {
        $('#itemTypeFilters .item-type-filter').prop('checked', true);
        filterTable();
    });

    // Select None button
    $('#selectNoneBtn').on('click', function() {
        $('#itemTypeFilters .item-type-filter').prop('checked', false);
        filterTable();
    });
});
