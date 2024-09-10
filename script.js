$(document).ready(function() {
    // Initialize DataTables
    const table = $('#publicationTable').DataTable({
        scrollX: false, // Enable horizontal scrolling
        scrollY: 1000,   // Set a fixed height for vertical scrolling (adjust as needed)
        scrollCollapse: true, // Enable scrollbars when needed
        paging: true, // Disable pagination
        pageLength: 50, //
        ordering: true, // Enable sorting
        order: [[4, 'desc']]
    });
});
