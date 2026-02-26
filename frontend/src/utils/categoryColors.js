export const CATEGORY_COLORS = {
    Food: {
        hex: '#F97316', // orange-500
        badgeClasses: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
        solidClasses: 'bg-orange-500 text-white',
    },
    Groceries: {
        hex: '#22C55E', // green-500
        badgeClasses: 'bg-green-500/10 text-green-400 border-green-500/20',
        solidClasses: 'bg-green-500 text-white',
    },
    Transport: {
        hex: '#3B82F6', // blue-500
        badgeClasses: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        solidClasses: 'bg-blue-500 text-white',
    },
    Utilities: {
        hex: '#A855F7', // purple-500
        badgeClasses: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
        solidClasses: 'bg-purple-500 text-white',
    },
    Entertainment: {
        hex: '#EC4899', // pink-500
        badgeClasses: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
        solidClasses: 'bg-pink-500 text-white',
    },
    Shopping: {
        hex: '#EAB308', // yellow-500
        badgeClasses: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
        solidClasses: 'bg-yellow-500 text-black', // contrast
    },
    Other: {
        hex: '#6B7280', // gray-500
        badgeClasses: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
        solidClasses: 'bg-gray-500 text-white',
    }
};

export const getCategoryColor = (categoryName) => {
    // Try exact match, otherwise default to "Other"
    if (categoryName && CATEGORY_COLORS[categoryName]) {
        return CATEGORY_COLORS[categoryName];
    }

    // Try case-insensitive matching
    const matchingKey = Object.keys(CATEGORY_COLORS).find(
        (key) => key.toLowerCase() === (categoryName || '').toLowerCase()
    );

    if (matchingKey) return CATEGORY_COLORS[matchingKey];

    return CATEGORY_COLORS.Other;
};
