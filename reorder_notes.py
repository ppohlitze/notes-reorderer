from typing import List, Dict, Tuple
import re
import PyPDF2  # We still need this for page dimensions
import os

def extract_page_dimensions(pdf_path: str) -> Dict[int, Tuple[float, float]]:
    """Extract page dimensions for each page in the PDF."""
    dimensions = {}
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num, page in enumerate(pdf_reader.pages, 1):
            dimensions[page_num] = (page.mediabox.width, page.mediabox.height)
    return dimensions

def parse_fdf_notes(fdf_path: str) -> Dict[int, List[Tuple[str, float, float]]]:
    """Parse FDF file and extract notes with their coordinates."""
    notes_by_page = {}
    
    with open(fdf_path, 'rb') as file:
        fdf_data = file.read().decode('utf-8', errors='ignore')
    
    # Updated regex pattern to handle escaped characters in content
    annotations = re.finditer(
        r'/Type/Annot/Subtype/Highlight.*?' # Identify highlight annotations
        r'/Rect\[(\d+\.?\d*) (\d+\.?\d*) (\d+\.?\d*) (\d+\.?\d*)\]'  # Capture rectangle coordinates
        r'.*?/Page (\d+)'  # Capture page number (0-based)
        r'.*?/Contents\(((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*)\)',  # Capture contents with nested parentheses
        fdf_data, re.DOTALL
    )
    
    for match in annotations:
        x1, y1, x2, y2 = map(float, match.groups()[:4])
        page = int(match.group(5)) + 1  # Convert to 1-based page numbers
        content = match.group(6)
        
        # Unescape special characters in content
        content = content.replace('\\(', '(').replace('\\)', ')').replace('\\\\', '\\')
        
        if page not in notes_by_page:
            notes_by_page[page] = []
        
        # Use center x coordinate and top y coordinate for positioning
        x_center = (x1 + x2) / 2
        y_top = max(y1, y2)
        
        note_text = f"* Highlight, page {page}\n{content}"
        notes_by_page[page].append((note_text, x_center, y_top))
    
    return notes_by_page

def reorder_notes_on_page(notes: List[Tuple[str, float, float]], page_width: float) -> List[str]:
    """
    Reorder notes based on their coordinates in the PDF.
    Uses x-coordinate to determine column and y-coordinate for vertical ordering.
    """
    # Determine column split point (usually middle of page)
    column_split = page_width / 2
    
    # Separate notes into left and right columns based on x-coordinate
    left_column = []
    right_column = []
    
    for note in notes:
        if note[1] < column_split:  # x-coordinate < middle of page
            left_column.append(note)
        else:
            right_column.append(note)
    
    # Sort each column by y-coordinate (top to bottom)
    left_column.sort(key=lambda x: -x[2])  # Negative because PDF coordinates start from bottom
    right_column.sort(key=lambda x: -x[2])
    
    # Combine columns (left then right) and extract just the text
    return [note[0] for note in left_column + right_column]

def write_reordered_notes(notes_by_page: Dict[int, List[Tuple[str, float, float]]], 
                         page_dimensions: Dict[int, Tuple[float, float]], 
                         output_path: str):
    """Write reordered notes to output file."""
    with open(output_path, 'w', encoding='utf-8') as file:
        for page_num in sorted(notes_by_page.keys()):
            page_width = page_dimensions[page_num][0]
            reordered_notes = reorder_notes_on_page(notes_by_page[page_num], page_width)
            
            # Write page header
            file.write(f"Page {page_num}\n")
            
            # Write notes for this page
            for note in reordered_notes:
                # Extract just the content part (remove the "* Highlight, page X" prefix)
                content = note.split('\n')[1]
                
                # Clean up question marks that aren't at the end
                if not content.endswith('?'):
                    content = content.replace('?', '')
                
                file.write(f"- {content}\n")
            
            # Add separator after each page (except the last page)
            if page_num != max(notes_by_page.keys()):
                file.write("\n----------\n\n")

def get_file_path(prompt: str) -> str:
    """Get file path from user and verify it exists."""
    while True:
        path = input(prompt).strip()
        if os.path.exists(path):
            return path
        print(f"Error: File not found at: {path}")

def main(pdf_path: str, notes_path: str, output_path: str):
    """Main function to process and reorder notes."""
    # Extract page dimensions from PDF
    page_dimensions = extract_page_dimensions(pdf_path)
    
    # Parse notes file
    notes_by_page = parse_fdf_notes(notes_path)
    
    # Write reordered notes
    write_reordered_notes(notes_by_page, page_dimensions, output_path)

if __name__ == "__main__":
    # Get file paths from user
    pdf_path = get_file_path("Enter the absolute path to the PDF file: ")
    notes_path = get_file_path("Enter the absolute path to the FDF notes file: ")
    output_path = input("Enter the absolute path for the output file: ").strip()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"Error: Could not create output directory: {e}")
            exit(1)
    
    main(pdf_path, notes_path, output_path)
