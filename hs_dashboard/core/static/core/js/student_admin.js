window.addEventListener('load', function () {
    // We use window.load to ensure all admin scripts (like jQuery) might have finished, 
    // though DOMContentLoaded is usually enough.

    const gradeSelect = document.getElementById('id_grade_level');
    // Django admin wraps fields in a div with class 'field-FIELDNAME'
    const customGradeRow = document.querySelector('.field-custom_grade_level');

    if (!gradeSelect || !customGradeRow) {
        console.warn('Student Admin JS: Elements not found', { gradeSelect, customGradeRow });
        return;
    }

    function toggleCustomGrade() {
        if (gradeSelect.value === 'Other') {
            customGradeRow.style.display = ''; // Reset to default (block/flex)
            // Also enable the input if it was disabled
            const input = customGradeRow.querySelector('input');
            if (input) input.disabled = false;
        } else {
            customGradeRow.style.display = 'none';
            // Disable input to prevent submission of hidden value if needed, 
            // though Django cleans it usually.
            const input = customGradeRow.querySelector('input');
            if (input) input.disabled = true;
        }
    }

    // Run on load
    toggleCustomGrade();

    // Run on change
    gradeSelect.addEventListener('change', toggleCustomGrade);
});
