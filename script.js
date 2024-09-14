$(document).ready(function () {
    // Initialize DataTables
    const table = $('#publicationTable').DataTable({
        scrollX: false, // Disable horizontal scrolling
        scrollY: 1000,   // Set a fixed height for vertical scrolling (adjust as needed)
        scrollCollapse: true, // Enable scrollbars when needed
        paging: true, // Enable pagination
        pageLength: 150, // Number of entries per page
        ordering: true, // Enable sorting
        order: [[4, 'desc']], // Sort by the 5th column (year) in descending order
        initComplete: function () {
            let publicationTable = this;
            const selectSearch = ['Item Type', 'Year']
            publicationTable.api()
                .columns()
                .every(function () {
                    let column = this;
                    let columnName = column.header().innerText;
                    let filterHeader = document.getElementById('_filter-' + columnName);

                    if (selectSearch.includes(columnName)) {
                        // Create select element
                        let select = document.createElement('select');
                        select.add(new Option(''));
                        filterHeader.replaceChildren(select);

                        // Apply listener for user change in value
                        select.addEventListener('change', () => {
                            column
                                .search(select.value, {exact: true})
                                .draw();
                        });

                        // Add list of options
                        let optionTexts = column.nodes()
                            .map((cell) => {
                                return cell.innerText;
                            })
                            .filter((value) => {
                                return value.length > 0;
                            })
                            .unique()
                            .sort();

                        if (columnName === 'Year') {
                            optionTexts = optionTexts.reverse();
                        }

                        optionTexts.each(function (o) {
                            if (o.length > 0) {
                                select.add(new Option(o));
                            }
                        });
                    } else {
                        // Create input element
                        let input = document.createElement('input');
                        input.placeholder = columnName;
                        filterHeader.replaceChildren(input);

                        // Event listener for user input
                        input.addEventListener('keyup', () => {
                            if (column.search() !== this.value) {
                                column.search(input.value).draw();
                            }
                        });
                    }
                });
            publicationTable.api().draw();
            window.addEventListener('resize', () => {
                publicationTable.api().draw();
            });
        }
    });
});
