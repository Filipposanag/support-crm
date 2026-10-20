-- Migration 025: Add PDF template positions for visual editor
-- Stores element positions and sizes for each PDF template type

-- Create pdf_templates table for storing template configurations
CREATE TABLE IF NOT EXISTS pdf_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_type VARCHAR(50) NOT NULL UNIQUE,
    template_name VARCHAR(255) NOT NULL,
    page_width DECIMAL(10,2) DEFAULT 595.0,
    page_height DECIMAL(10,2) DEFAULT 842.0,
    margin_top DECIMAL(10,2) DEFAULT 50.0,
    margin_bottom DECIMAL(10,2) DEFAULT 50.0,
    margin_left DECIMAL(10,2) DEFAULT 50.0,
    margin_right DECIMAL(10,2) DEFAULT 50.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create pdf_template_elements table for storing element positions
CREATE TABLE IF NOT EXISTS pdf_template_elements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id INT NOT NULL,
    element_type VARCHAR(50) NOT NULL,
    element_name VARCHAR(255) NOT NULL,
    pos_x DECIMAL(10,2) NOT NULL DEFAULT 0,
    pos_y DECIMAL(10,2) NOT NULL DEFAULT 0,
    width DECIMAL(10,2) DEFAULT 100,
    height DECIMAL(10,2) DEFAULT 30,
    font_size INT DEFAULT 12,
    font_bold TINYINT(1) DEFAULT 0,
    font_italic TINYINT(1) DEFAULT 0,
    text_align VARCHAR(20) DEFAULT 'left',
    visible TINYINT(1) DEFAULT 1,
    z_order INT DEFAULT 0,
    custom_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES pdf_templates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default templates
INSERT IGNORE INTO pdf_templates (template_type, template_name) VALUES 
    ('family', 'Βεβαίωση Οικογένειας'),
    ('payment', 'Απόδειξη Πληρωμής'),
    ('subscription', 'Βεβαίωση Συνδρομής');

-- Insert default elements for family template
INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'logo', 'Λογότυπο', 50, 30, 80, 80, 12, 'left' FROM pdf_templates WHERE template_type = 'family';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, font_bold, text_align) 
SELECT id, 'org_name', 'Όνομα Συλλόγου', 150, 50, 400, 30, 16, 1, 'center' FROM pdf_templates WHERE template_type = 'family';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, font_bold, text_align) 
SELECT id, 'title', 'Τίτλος', 50, 120, 495, 30, 18, 1, 'center' FROM pdf_templates WHERE template_type = 'family';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'date', 'Ημερομηνία', 400, 160, 145, 20, 11, 'right' FROM pdf_templates WHERE template_type = 'family';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'content', 'Περιεχόμενο', 50, 200, 495, 400, 12, 'left' FROM pdf_templates WHERE template_type = 'family';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'signature', 'Υπογραφή', 350, 650, 195, 60, 12, 'center' FROM pdf_templates WHERE template_type = 'family';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'footer', 'Υποσέλιδο', 50, 780, 495, 40, 9, 'center' FROM pdf_templates WHERE template_type = 'family';

-- Insert default elements for payment template
INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'logo', 'Λογότυπο', 50, 30, 80, 80, 12, 'left' FROM pdf_templates WHERE template_type = 'payment';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, font_bold, text_align) 
SELECT id, 'org_name', 'Όνομα Συλλόγου', 150, 50, 400, 30, 16, 1, 'center' FROM pdf_templates WHERE template_type = 'payment';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, font_bold, text_align) 
SELECT id, 'title', 'Τίτλος', 50, 120, 495, 30, 18, 1, 'center' FROM pdf_templates WHERE template_type = 'payment';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'date', 'Ημερομηνία', 400, 160, 145, 20, 11, 'right' FROM pdf_templates WHERE template_type = 'payment';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, font_bold, text_align) 
SELECT id, 'amount', 'Ποσό', 50, 300, 495, 40, 20, 1, 'center' FROM pdf_templates WHERE template_type = 'payment';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'content', 'Περιεχόμενο', 50, 200, 495, 350, 12, 'left' FROM pdf_templates WHERE template_type = 'payment';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'signature', 'Υπογραφή', 350, 650, 195, 60, 12, 'center' FROM pdf_templates WHERE template_type = 'payment';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'footer', 'Υποσέλιδο', 50, 780, 495, 40, 9, 'center' FROM pdf_templates WHERE template_type = 'payment';

-- Insert default elements for subscription template
INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'logo', 'Λογότυπο', 50, 30, 80, 80, 12, 'left' FROM pdf_templates WHERE template_type = 'subscription';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, font_bold, text_align) 
SELECT id, 'org_name', 'Όνομα Συλλόγου', 150, 50, 400, 30, 16, 1, 'center' FROM pdf_templates WHERE template_type = 'subscription';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, font_bold, text_align) 
SELECT id, 'title', 'Τίτλος', 50, 120, 495, 30, 18, 1, 'center' FROM pdf_templates WHERE template_type = 'subscription';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'date', 'Ημερομηνία', 400, 160, 145, 20, 11, 'right' FROM pdf_templates WHERE template_type = 'subscription';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'content', 'Περιεχόμενο', 50, 200, 495, 400, 12, 'left' FROM pdf_templates WHERE template_type = 'subscription';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'signature', 'Υπογραφή', 350, 650, 195, 60, 12, 'center' FROM pdf_templates WHERE template_type = 'subscription';

INSERT IGNORE INTO pdf_template_elements (template_id, element_type, element_name, pos_x, pos_y, width, height, font_size, text_align) 
SELECT id, 'footer', 'Υποσέλιδο', 50, 780, 495, 40, 9, 'center' FROM pdf_templates WHERE template_type = 'subscription';
