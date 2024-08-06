label: function(context) {
    console.log('Full context object:', context);
    console.log('Dataset label:', context.dataset.label);
    console.log('Parsed Y value:', context.parsed.y);
    console.log('Raw data:', context.raw);

    let label = context.dataset.label || '';
    if (label) {
        label += ': ';
    }
    if (context.parsed.y !== null) {
        label += `Length: ${context.parsed.y}in, `;
    }
    if (context.raw.indication_number) {
        label += `Number: ${context.raw.indication_number}, `;
    }
    if (context.raw.axial_start) {
        label += `Axial Start: ${context.raw.axial_start}ft, `;
    }
    if (context.raw.width) {
        label += `Width: ${context.raw.width}in, `;
    }
    if (context.raw.clock_position) {
        label += `Clock: ${context.raw.clock_position}`;
    }

    console.log('Final label:', label);
    return label;
}