$(document).ready(function() {
    // Initialize DataTables
    const table = $('#publicationTable').DataTable({
        scrollX: false, // Disable horizontal scrolling
        scrollY: 1000,   // Set a fixed height for vertical scrolling (adjust as needed)
        scrollCollapse: true, // Enable scrollbars when needed
        paging: true, // Enable pagination
        pageLength: 150, // Number of entries per page
        ordering: true, // Enable sorting
        order: [[4, 'desc']] // Sort by the 5th column (year) in descending order
    });
});
